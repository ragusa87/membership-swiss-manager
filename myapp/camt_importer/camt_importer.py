from django.db.models import Q
from pycamt.parser import Camt053Parser
from myapp.models import Invoice, Subscription
from difflib import SequenceMatcher


class MyCamt053Parser(Camt053Parser):
    def _extract_common_entry_data(self, entry):
        data = super()._extract_common_entry_data(entry)

        reference = entry.find(".//RmtInf/Strd/CdtrRefInf/Ref", self.namespaces)
        data["Reference"] = reference.text if reference is not None else None

        return data

    def _extract_transaction_details(self, tx_detail):
        detail = super()._extract_transaction_details(tx_detail)
        detail["TxId"] = (
            tx_detail.find(".//Refs//TxId", self.namespaces).text
            if tx_detail.find(".//Refs//TxId", self.namespaces) is not None
            else None
        )

        debtor_address = tx_detail.find(".//RltdPties/Dbtr/PstlAdr", self.namespaces)
        if debtor_address is not None:
            debtor_address = {
                child.tag.split("}")[1]: child.text for child in debtor_address
            }
        detail["DbtrPstlAdr"] = debtor_address

        return detail


def is_bonification(additionalEntryInformation: str) -> bool:
    return additionalEntryInformation.lower().startswith("bonification")


def is_same_user(invoice: Invoice | None, additionalEntryInformation: str) -> bool:
    if invoice is None or additionalEntryInformation == "":
        return False
    if not is_bonification(additionalEntryInformation):
        return False

    name = (
        additionalEntryInformation.lower().replace("bonification", "").strip().lower()
    )
    invoice_member = invoice.member_subscription.member
    if invoice_member is None:
        return False

    similarity1 = SequenceMatcher(
        None, name, invoice_member.get_fullname().lower()
    ).ratio()
    similarity2 = SequenceMatcher(
        None, name, invoice_member.get_fullname_inverted().lower()
    ).ratio()

    return max(similarity1, similarity2) >= 0.9


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
                sign * int(float(self.data["Amount"]) * 100)
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

        return self.__getattr__("price") != self.invoice.price

    def is_same_user(self) -> bool:
        if self.invoice is None:
            return False

        return is_same_user(self.invoice, str(self.data["AdditionalEntryInformation"]))

    def isBonification(self):
        return is_bonification(str(self.data["AdditionalEntryInformation"]))

    def valid(self) -> bool:
        return (
            self.invoice is not None
            and self.invoice.price == self.__getattr__("price")
            and self.data["Currency"] == "CHF"
            and self.invoice.transaction_id == self.data["TxId"]
        )


class CamtImporter:
    def __init__(self, file, subscription: Subscription | None = None):
        self.parser = MyCamt053Parser(file.read().decode("utf-8"))
        self.invoices = self.__import_invoices__(subscription)

    def transactions(self) -> list[Transaction]:
        result = []
        for transaction in self.parser.get_transactions():
            result.append(
                Transaction(
                    transaction,
                    self.__find_invoice__(
                        transaction["TxId"],
                        transaction["Reference"],
                        transaction["AdditionalEntryInformation"],
                    ),
                )
            )
        return result

    def __import_invoices__(self, subscription: Subscription | None) -> list[Invoice]:
        transactions = []
        references = []
        for t in self.parser.get_transactions():
            if "TxId" in t and t["TxId"] is not None:
                transactions.append(t["TxId"])
            if "Reference" in t and t["Reference"] is not None:
                int_value = get_reference_as_int(t["Reference"])
                if int_value is not None:
                    references.append(int_value)

        query = (
            Invoice.objects.filter(
                Q(transaction_id__in=transactions)
                | Q(reference__in=references)
                | Q(pk__in=references)
            )
            .select_related("member_subscription")
            .prefetch_related("member_subscription__member")
        )
        if subscription is not None:
            query = query.filter(member_subscription_subscription=subscription)

        return [i for i in query.all()]

    def __find_invoice__(
        self,
        transaction_id: str | None,
        score_reference: str | None,
        additionalEntryInformation: None | str,
    ):
        for invoice in self.invoices:
            if transaction_id is not None and invoice.transaction_id == transaction_id:
                invoice.reason = "transaction_id"
                return invoice

        for invoice in self.invoices:
            int_value = get_reference_as_int(score_reference)
            if (
                int_value is not None
                and invoice.get_reference() == int_value
                and additionalEntryInformation is not None
                and is_same_user(invoice, additionalEntryInformation)
            ):
                invoice.reason = "reference_id"
                return invoice

        return None
