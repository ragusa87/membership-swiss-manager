import html
import re
from difflib import SequenceMatcher

from django.db.models import Q
from pycamt.parser import Camt053ParseError, Camt053Parser

from core.models import Invoice, InvoiceStatusEnum, Subscription
from core.utils import chf_to_centimes


def strip_namespaces(root) -> None:
    """Rewrite every element tag in-place to drop its XML namespace.

    pycamt >= 1.1 queries the tree with unprefixed XPaths (``.//Stmt``)
    while exposing ``self.namespaces`` as lxml's ``nsmap`` (which maps the
    default namespace to ``None``). lxml's ``findall`` cannot use a ``None``
    prefix, so those queries silently match nothing on namespaced CAMT
    documents. Stripping the namespaces lets both pycamt's and our own
    unprefixed XPaths resolve.
    """
    for element in root.iter():
        tag = element.tag
        if isinstance(tag, str) and "}" in tag:
            element.tag = tag.split("}", 1)[1]


class CamtParser(Camt053Parser):
    """CAMT parser handling camt.052 (Rpt), camt.053 (Stmt) and camt.054 (Ntfctn).

    pycamt only ships a camt.053 parser, but the three message types share the
    same entry/transaction structure, so we extend it and teach
    ``_find_statements_or_reports`` about the extra top-level containers.
    """

    def __init__(self, xml_data: str | bytes):
        # lxml rejects a decoded str that still carries an encoding
        # declaration, so always hand it bytes.
        if isinstance(xml_data, str):
            xml_data = xml_data.encode("utf-8")
        # The parent parses and detects the version while namespaces are
        # still present; strip them afterwards so all XPaths resolve.
        super().__init__(xml_data)
        strip_namespaces(self.tree)
        self.namespaces = {}

    def get_transactions(self):
        # Some banks double-encode entities in free-text fields, so the XML
        # carries "&amp;amp;". lxml decodes it once to "&amp;"; unescape once more
        # to get "&", otherwise it renders as "&amp;" and breaks name matching
        # (which splits joint payers on "&"). Ids/references carry no entities,
        # so this is a no-op for them.
        return [
            {
                key: html.unescape(value) if isinstance(value, str) else value
                for key, value in transaction.items()
            }
            for transaction in super().get_transactions()
        ]

    def _find_statements_or_reports(self):
        # camt.053 uses Stmt, camt.052 uses Rpt, camt.054 uses Ntfctn.
        for xmlpath in (".//Stmt", ".//Rpt", ".//Ntfctn"):
            found = self.tree.findall(xmlpath, self.namespaces)
            if found:
                return found
        raise Camt053ParseError()

    def _find_text(self, element, path):
        if element is None:
            return None
        node = element.find(path, self.namespaces)
        return node.text if node is not None else None

    def _extract_common_entry_data(self, entry, statement):
        data = super()._extract_common_entry_data(entry, statement)
        data["Reference"] = self._find_text(entry, ".//RmtInf/Strd/CdtrRefInf/Ref")
        return data

    def _extract_transaction_details(self, tx_detail):
        detail = super()._extract_transaction_details(tx_detail)

        detail["TxId"] = (
            self._find_text(tx_detail, ".//Refs//TxId")
            or self._find_text(tx_detail, ".//Refs//InstrId")
            or self._find_text(tx_detail, ".//Refs//EndToEndId")
            or self._find_text(tx_detail, ".//Refs//UETR")
        )

        detail["UltmtDbtr"] = (
            tx_detail.find(".//UltmtDbtr//Nm", self.namespaces).text
            if tx_detail.find(".//UltmtDbtr", self.namespaces) is not None
            else None
        )

        debtor_address = tx_detail.find(".//RltdPties/Dbtr/PstlAdr", self.namespaces)
        if debtor_address is not None:
            debtor_address = {
                child.tag.split("}")[-1]: child.text for child in debtor_address
            }
        detail["DbtrPstlAdr"] = debtor_address

        detail["Reference"] = self._find_text(
            tx_detail, ".//RmtInf/Strd/CdtrRefInf/Ref"
        )

        # pycamt >= 1.1 overwrites RemittanceInformation with the structured
        # creditor reference whenever Strd is present. We expose that reference
        # separately (see Reference above), so keep RemittanceInformation as the
        # human-readable message: unstructured Ustrd, else the additional Strd
        # remittance info.
        detail["RemittanceInformation"] = self._find_text(
            tx_detail, ".//RmtInf/Ustrd"
        ) or self._find_text(tx_detail, ".//RmtInf/Strd/AddtlRmtInf")

        if not detail.get("CreditorName"):
            detail["CreditorName"] = self._find_text(self.tree, ".//Acct/Ownr/Nm")

        return detail


BONIFICATION_PREFIXES = ("bonification", "gutschrift")


def is_bonification(additionalEntryInformation: str) -> bool:
    info = additionalEntryInformation.lower()
    return any(info.startswith(prefix) for prefix in BONIFICATION_PREFIXES)


def _name_tokens(name: str) -> set[str]:
    return {token for token in name.lower().replace("&", " ").split() if token}


def name_matches_invoice(invoice: Invoice | None, name: str | None) -> bool:
    if invoice is None or not name:
        return False
    invoice_member = invoice.member_subscription.member
    if invoice_member is None:
        return False

    name_lower = name.lower().strip()
    fullname = invoice_member.get_fullname().lower()
    fullname_inverted = invoice_member.get_fullname_inverted().lower()

    # Signal 1: overall sequence similarity (handles typos / small differences)
    similarity1 = SequenceMatcher(None, name_lower, fullname).ratio()
    similarity2 = SequenceMatcher(None, name_lower, fullname_inverted).ratio()
    if max(similarity1, similarity2) >= 0.9:
        return True

    # Signal 2: token subset — every part of the member name appears in the
    # transaction name (handles married / middle names in bank statements,
    # e.g. member "Jane Doe" vs statement "JANE DOE VAN SMITH").
    # Requires at least two member tokens to avoid single-common-name matches.
    member_tokens = _name_tokens(fullname)
    return len(member_tokens) >= 2 and member_tokens.issubset(_name_tokens(name_lower))


def is_same_user(invoice: Invoice | None, additionalEntryInformation: str) -> bool:
    if invoice is None or additionalEntryInformation == "":
        return False
    if not is_bonification(additionalEntryInformation):
        return False

    name = additionalEntryInformation.lower()
    for prefix in BONIFICATION_PREFIXES:
        name = name.replace(prefix, "")
    name = name.strip()

    # Split on common separators ("&", " et ", " and ") and try each name
    # individually. Word separators are matched on whole-word boundaries so
    # names that merely contain the letters "et"/"and" are not shredded.
    for single_name in re.split(r"\s+(?:et|and)\s+|&", name):
        single_name = single_name.strip()
        if single_name and name_matches_invoice(invoice, single_name):
            return True

    # Also try the full name in case there's no separator
    return name_matches_invoice(invoice, name)


def get_reference_as_int(value: str | None) -> int | None:
    if value is None:
        return None
    if str(value)[0:2] != "RF":
        return None
    value = str(value[4:]).lstrip("0")
    if len(value) < 10:
        return int(value)
    return None


class Transaction:
    def __init__(self, data: dict, invoice: Invoice | None):
        self.data = data
        self.invoice = invoice

    def __repr__(self):
        return str(self.data)

    def __getattr__(self, attr):
        if attr == "price":
            sign = -1 if self.data["CreditDebitIndicator"] == "DBIT" else 1

            return (
                sign * chf_to_centimes(self.data["Amount"])
                if "Amount" in self.data
                else 0
            )
        if attr == "invoice":
            return self.invoice

        if attr not in self.data:
            raise AttributeError(name=attr, obj=self)

        return self.data[attr]

    def price_mismatch(self):
        if self.invoice is None:
            return False

        return self.price != self.invoice.price

    @property
    def additional_info(self) -> str:
        return str(
            self.data.get("AdditionalEntryInformation")
            or self.data.get("RemittanceInformation")
            or ""
        )

    # Per-transaction identifiers, stable across imports. The one we store when
    # reconciling (see tx_id) comes from this group.
    STRONG_ID_FIELDS = ("TxId", "EndToEndId", "InstrId", "UETR")
    # Batch-level bank references (pycamt exposes AcctSvcrRef as TransactionID).
    # These are shared by every transaction of the same booking, so they are not
    # a reliable per-transaction identity — kept only as a weak fallback.
    WEAK_ID_FIELDS = ("AcctSvcrRef", "TransactionID")

    @property
    def tx_id(self) -> str | None:
        for field in (*self.STRONG_ID_FIELDS, *self.WEAK_ID_FIELDS):
            value = self.data.get(field)
            if value:
                return value
        return None

    @property
    def strong_tx_ids(self) -> list[str]:
        return self._collect_ids(self.STRONG_ID_FIELDS)

    @property
    def weak_tx_ids(self) -> list[str]:
        return self._collect_ids(self.WEAK_ID_FIELDS)

    @property
    def candidate_tx_ids(self) -> list[str]:
        """All identifiers this transaction legitimately carries.

        An invoice reconciled against any of them (possibly an older parser's
        resolution) should still match. Strong per-transaction ids come first,
        batch-level ones last.
        """
        return self._collect_ids((*self.STRONG_ID_FIELDS, *self.WEAK_ID_FIELDS))

    def _collect_ids(self, fields) -> list[str]:
        result = []
        for field in fields:
            value = self.data.get(field)
            if value and value not in result:
                result.append(value)
        return result

    @property
    def reference(self) -> str | None:
        return self.data.get("Reference") or self.data.get("AcctSvcrRef")

    def is_same_user(self) -> bool:
        if self.invoice is None:
            return False

        if is_same_user(self.invoice, self.additional_info):
            return True
        if name_matches_invoice(self.invoice, self.data.get("DebtorName")):
            return True
        return bool(name_matches_invoice(self.invoice, self.data.get("UltmtDbtr")))

    def isBonification(self):
        return is_bonification(self.additional_info)

    def valid(self) -> bool:
        return (
            self.invoice is not None
            and self.invoice.price == self.price
            and self.data.get("Currency") == "CHF"
            and self.invoice.transaction_id is not None
            and self.invoice.transaction_id in self.candidate_tx_ids
        )


class CamtImporter:
    def __init__(self, file, subscription: Subscription | None = None):
        self.parser = CamtParser(file.read())
        # Parse once and reuse: get_transactions() re-parses the XML on each call.
        self.raw_transactions = list(self.parser.get_transactions())
        # Batch-level references shared by several transactions cannot identify a
        # single one, so they are excluded from transaction_id matching.
        self._ambiguous_weak_ids = self.__compute_ambiguous_weak_ids__()
        self.invoices = self.__import_invoices__(subscription)

    def __compute_ambiguous_weak_ids__(self) -> set[str]:
        counts: dict[str, int] = {}
        for data in self.raw_transactions:
            for weak_id in Transaction(data, None).weak_tx_ids:
                counts[weak_id] = counts.get(weak_id, 0) + 1
        return {weak_id for weak_id, count in counts.items() if count > 1}

    def _match_tx_ids(self, tx: Transaction) -> list[str]:
        """Identifiers usable to match this transaction to an invoice.

        Strong per-transaction ids are always usable; batch-level ids only when
        they are unique in the file (a shared batch ref would bind unrelated
        transactions to the same invoice).
        """
        ids = list(tx.strong_tx_ids)
        for weak_id in tx.weak_tx_ids:
            if weak_id not in self._ambiguous_weak_ids and weak_id not in ids:
                ids.append(weak_id)
        return ids

    def transactions(self) -> list[Transaction]:
        result = []
        for data in self.raw_transactions:
            tx = Transaction(data, None)
            tx.invoice = self.__find_invoice__(
                self._match_tx_ids(tx),
                tx.reference,
                tx.additional_info,
                data.get("DebtorName"),
                data.get("UltmtDbtr"),
            )
            result.append(tx)
        return result

    def __import_invoices__(self, subscription: Subscription | None) -> list[Invoice]:
        transactions = []
        references = []
        for t in self.raw_transactions:
            # Load invoices reconciled against any matchable id (an older parser
            # may have stored a batch-level id such as AcctSvcrRef), so they can
            # still be re-matched.
            transactions.extend(self._match_tx_ids(Transaction(t, None)))
            if t.get("Reference") is not None:
                int_value = get_reference_as_int(t["Reference"])
                if int_value is not None:
                    references.append(int_value)

        # Build base query with transaction ID and reference matches.
        # Not scoped to the subscription on purpose: matching across all
        # subscriptions lets the UI warn about subscription mismatches.
        query = (
            Invoice.objects.filter(
                Q(transaction_id__in=transactions)
                | Q(reference__in=references)
                | Q(pk__in=references)
            )
            .select_related("member_subscription")
            .prefetch_related("member_subscription__member")
        )

        invoices = list(query.all())

        # Also add unpaid invoices from the subscription for name-based matching
        # (handles cases where reference/transaction_id are not yet set)
        # Only include invoices for members with no parent (main account holders)
        if subscription is not None:
            unpaid_query = (
                Invoice.objects.filter(
                    member_subscription__subscription=subscription,
                    member_subscription__parent__isnull=True,
                    status__in=[InvoiceStatusEnum.CREATED, InvoiceStatusEnum.PENDING],
                )
                .select_related("member_subscription")
                .prefetch_related("member_subscription__member")
            )
            # Avoid duplicates by checking which ones are already in the list
            existing_ids = {inv.id for inv in invoices}
            unpaid_invoices = [
                inv for inv in unpaid_query.all() if inv.id not in existing_ids
            ]
            invoices.extend(unpaid_invoices)

        return invoices

    def __find_invoice__(
        self,
        transaction_ids: list[str],
        score_reference: str | None,
        additionalEntryInformation: None | str,
        debtor_name: str | None = None,
        ultimate_debtor: str | None = None,
    ):
        for invoice in self.invoices:
            if (
                invoice.transaction_id is not None
                and invoice.transaction_id in transaction_ids
            ):
                invoice.reason = "transaction_id"
                return invoice

        for invoice in self.invoices:
            int_value = get_reference_as_int(score_reference)
            if int_value is None or invoice.get_reference() != int_value:
                continue
            if additionalEntryInformation is not None and is_same_user(
                invoice, additionalEntryInformation
            ):
                invoice.reason = "reference_id"
                return invoice
            if name_matches_invoice(invoice, debtor_name) or name_matches_invoice(
                invoice, ultimate_debtor
            ):
                invoice.reason = "reference_id"
                return invoice

        # Stage 3: Match by bonification name without reference.
        # A "A & B" bonification is assumed to be a single household paying one
        # invoice, so the first name-matching invoice is returned without an
        # amount check. If independent members ever combine one payment for
        # separate invoices, add amount-based disambiguation / ambiguity
        # handling here.
        for invoice in self.invoices:
            if additionalEntryInformation and is_same_user(
                invoice, additionalEntryInformation
            ):
                invoice.reason = "bonification_name"
                return invoice

        return None
