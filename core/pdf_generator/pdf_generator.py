import base64
import io
from collections import OrderedDict
from io import StringIO
from pathlib import Path
import cairosvg
from pypdf import PdfWriter, PdfReader
import locale
from ..models import (
    Invoice,
    Member,
    MemberSubscription,
    Subscription,
    SubscriptionTypeEnum,
    InvoiceStatusEnum,
)
from django.utils import translation
from contextlib import ContextDecorator
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from qrbill import QRBill
from stdnum.iso11649 import is_valid
from qrbill.bill import QR_IID
import svgwrite
from qrbill.bill import A4, mm


class Position:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def move(self, x: int, y: int):
        self.x += x
        self.y += y
        return self

    def set(self, x: int, y: int):
        self.x = x
        self.y = y

    def as_tuple(self) -> tuple:
        return (self.x, self.y)


def get_locale(language_code):
    locale_map = {
        "FR": "fr_CH.utf8",  # French (Switzerland)
        "EN": "en_US.utf8",  # English (United States)
    }
    return locale_map.get(
        language_code.upper(), "en_US.utf8"
    )  # Default to en_US.utf8 if not found


class TranslationContext(ContextDecorator):
    locale_map = {
        "FR": "fr_CH.utf8",  # French (Switzerland)
        "EN": "en_US.utf8",  # English (United States)
    }

    def __init__(self, language_code):
        self.language_code = language_code
        self.locale_time = (
            self.locale_map[language_code.upper()]
            if language_code.upper() in self.locale_map
            else None
        )
        self.backup_locale_time = locale.getlocale(category=locale.LC_TIME)

    def __enter__(self):
        translation.activate(self.language_code)
        if self.locale_time is not None:
            try:
                locale.setlocale(locale.LC_TIME, self.locale_time)
            except locale.Error as e:
                print("Error " + str(e))
                locale.setlocale(locale.LC_TIME, "")  # Use system default

    def __exit__(self, *args):
        translation.deactivate()
        locale.setlocale(locale.LC_TIME, self.backup_locale_time)


class PDFGenerator:
    LOGO_PATH = Path(__file__).parent / "logo.svg"
    BRAND_COLOR = "#036045"
    MUTED_COLOR = "#555555"
    PAGE_WIDTH = mm(A4[0])
    MARGIN = 20
    HEADER_BOTTOM_Y = 115
    # Shared left edge for FACTURE title, recipient block, and total amount value.
    VALUE_COLUMN_X = 560

    def __init__(self):
        pass

    def __get_logo_data_uri__(self) -> str:
        encoded = base64.b64encode(self.LOGO_PATH.read_bytes()).decode("ascii")
        return f"data:image/svg+xml;base64,{encoded}"

    def __get_debtor__(self, member: Member) -> dict:
        return {
            "name": member.get_fullname(),
            "pcode": str(member.zip)
            if member.zip is not None
            else settings.CREDITOR_ZIP,
            "street": member.address,
            "house_num": member.address_number,
            "city": member.city if member.city else settings.CREDITOR_CITY,
            "country": member.get_country(),
        }

    def __get_creditor__(self) -> dict:
        return {
            "name": settings.CREDITOR_NAME,
            "pcode": settings.CREDITOR_ZIP,
            "street": settings.CREDITOR_ADDRESS,
            "house_num": settings.CREDITOR_ADDRESS_HOUSE_NUMBER,
            "city": settings.CREDITOR_CITY,
            "country": settings.CREDITOR_COUNTRY,
        }

    def __get_additional_information__(self, invoice: Invoice) -> str:
        type: str = invoice.member_subscription.get_type_text()
        name: str = invoice.member_subscription.subscription.name
        reminder_text: str = (
            invoice.get_reminder_text() + " - " if invoice.reminder > 0 else ""
        )
        if invoice.status == InvoiceStatusEnum.CANCELED:
            reminder_text += _("** Cancelled **")
        if invoice.status == InvoiceStatusEnum.PAID:
            reminder_text += _("** Paid **")

        return str(f"{reminder_text} {type} {name}")

    def __isIbanCompatibleWithQRCodeReference__(self, iban: str) -> bool:
        iban = iban.replace(" ", "")
        iban = iban.rjust(9, "0")
        qr_iid = int(iban[4:9])
        # QR_IID = {"start": 30000, "end": 31999}
        return QR_IID["start"] <= qr_iid <= QR_IID["end"]

    @staticmethod
    def __replace_chars__(s):
        return "".join(str(ord(c) - ord("A") + 10) if c.isalpha() else c for c in s)

    def __mod97_10__(self, reference: str) -> str:
        # Remove prefix "RF"
        # Inspired from https://github.com/kmukku/php-iso11649/blob/master/src/phpIso11649.php
        if reference[:2].upper() == "RF":
            reference = reference[2:]

        pre_result = reference + "RF00"
        pre_result = self.__replace_chars__(pre_result)
        checksum = 98 - (int(pre_result) % 97)
        checksum = str(checksum).zfill(2)
        return checksum

    def __generate_scor_reference__(self, reference: int) -> str:
        """
        Convert a reference number to a score reference (Ex: 539007547034 -> RF18539007547034)
        """
        if reference is not None and reference <= 0:
            raise RuntimeError("Reference number must be positive")

        if self.__isIbanCompatibleWithQRCodeReference__(
            settings.INVOICE_CUSTOMER_IDENTIFICATION_NUMBER
        ):
            raise RuntimeError("QRR is not supported yet")

        reference = str(reference).rjust(21, "0")

        full_reference = "RF" + str(self.__mod97_10__(reference)).zfill(2) + reference

        if not is_valid(full_reference):
            raise RuntimeError(f"Invalid reference: {full_reference}")

        return full_reference

    def generate_pdf(self, invoices: list[Invoice]) -> io.BytesIO:
        writer = PdfWriter()
        for invoice in invoices:
            reader = PdfReader(self.__generate_pdf__(invoice))
            writer.append(reader)

        result = io.BytesIO()
        writer.write(result)
        result.seek(0)

        return result

    def __svg2Pdf__(self, buffer: StringIO) -> io.BytesIO:
        byte_data = buffer.getvalue().encode("utf-8")
        byte_io = io.BytesIO(byte_data)

        pdf_output = io.BytesIO()
        cairosvg.svg2pdf(bytestring=byte_io.read(), write_to=pdf_output)

        return pdf_output

    def __generate_pdf__(self, invoice: Invoice) -> io.BytesIO:
        """
        Generate an invoice as SVG
        """
        svg_buffer = StringIO()

        with TranslationContext(settings.INVOICE_LANGUAGE):
            member = invoice.member_subscription.member
            bill = QRBill(
                settings.INVOICE_IBAN,
                creditor=self.__get_creditor__(),
                debtor=self.__get_debtor__(member),
                amount=str(invoice.price_decimal()),
                language=settings.INVOICE_LANGUAGE,
                reference_number=self.__generate_scor_reference__(
                    invoice.get_reference()
                ),
                additional_information=self.__get_additional_information__(invoice),
            )

            # A4 page with a white background
            dwg = svgwrite.Drawing(
                size=A4,
                viewBox=("0 0 %f %f" % (mm(A4[0]), mm(A4[1]))),
                debug=False,
            )
            dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill="white"))

            # Draw header
            pos = self.__draw_invoice_logo__(dwg, document_title=str(_("Invoice")))
            self.__draw_invoice_header__(dwg, pos, invoice)

            # Draw a bill and make it A4
            group = bill.draw_bill(dwg, True)
            bill.transform_to_full_page(dwg, group)

            dwg.write(svg_buffer)

            return self.__svg2Pdf__(svg_buffer)

    def __draw_invoice_logo__(self, dwg, document_title: str | None = None):
        dwg.add(
            dwg.image(
                href=self.__get_logo_data_uri__(),
                insert=(self.MARGIN, self.MARGIN),
                size=("80px", "80px"),
                preserveAspectRatio="xMidYMid meet",
            )
        )

        # Creditor block (name + address) to the right of the logo
        dwg.add(
            dwg.text(
                settings.CREDITOR_NAME,
                insert=(120, 48),
                fill="black",
                font_size="20px",
                font_weight="bold",
                font_family="Arial",
            )
        )
        dwg.add(
            dwg.text(
                f"{settings.CREDITOR_ADDRESS} {settings.CREDITOR_ADDRESS_HOUSE_NUMBER}".strip(),
                insert=(120, 70),
                fill=self.MUTED_COLOR,
                font_size="11px",
                font_family="Arial",
            )
        )
        dwg.add(
            dwg.text(
                f"{settings.CREDITOR_ZIP} {settings.CREDITOR_CITY}".strip(),
                insert=(120, 85),
                fill=self.MUTED_COLOR,
                font_size="11px",
                font_family="Arial",
            )
        )

        # Document title (top-right), aligned with creditor name baseline
        if document_title:
            dwg.add(
                dwg.text(
                    document_title.upper(),
                    insert=(self.VALUE_COLUMN_X, 56),
                    fill=self.BRAND_COLOR,
                    font_size="28px",
                    font_weight="bold",
                    font_family="Arial",
                    letter_spacing="2",
                )
            )

        # Accent rule under the header
        dwg.add(
            dwg.line(
                start=(self.MARGIN, self.HEADER_BOTTOM_Y),
                end=(self.PAGE_WIDTH - self.MARGIN, self.HEADER_BOTTOM_Y),
                stroke=self.BRAND_COLOR,
                stroke_width=1.5,
            )
        )

        return Position(self.MARGIN, self.HEADER_BOTTOM_Y)

    def __draw_invoice_header__(self, dwg, pos, invoice: Invoice):
        self.__draw_recipient_block__(dwg, invoice)
        self.__draw_invoice_metadata__(dwg, invoice)
        self.__draw_status_watermark__(dwg, invoice)
        return pos

    def __draw_recipient_block__(self, dwg, invoice: Invoice):
        """Draws the recipient address block at the envelope-window position.

        The parent member is billed; children are listed under the parent name,
        but the address shown is always the parent's.
        """
        parent_sub = invoice.member_subscription
        parent = parent_sub.member
        x = self.VALUE_COLUMN_X
        y = 175
        line_h = 16

        dwg.add(
            dwg.text(
                parent.get_fullname(),
                insert=(x, y),
                fill="black",
                font_size="13px",
                font_weight="bold",
                font_family="Arial",
            )
        )
        y += line_h

        for child_sub in MemberSubscription.objects.filter(parent=parent_sub):
            dwg.add(
                dwg.text(
                    "& " + child_sub.member.get_fullname(),
                    insert=(x, y),
                    fill="black",
                    font_size="13px",
                    font_family="Arial",
                )
            )
            y += line_h

        y += 6

        for line in (
            parent.get_full_address_line1(),
            parent.get_full_address_line2(),
        ):
            if not line:
                continue
            dwg.add(
                dwg.text(
                    line,
                    insert=(x, y),
                    fill="black",
                    font_size="13px",
                    font_family="Arial",
                )
            )
            y += line_h

    def __draw_metadata_table__(
        self,
        dwg,
        rows: list[tuple[str, str]],
        amount,
        amount_label: str | None = None,
    ):
        """Draws a label/value table followed by a separator and a total amount line.

        Labels and values are left-aligned in two columns; the total amount
        value starts at the same x as the row values so the column stays clean.
        """
        x_label = self.MARGIN
        x_value = self.VALUE_COLUMN_X
        x_right = self.PAGE_WIDTH - self.MARGIN
        y = 310
        line_h = 22

        for label, value in rows:
            text = dwg.text(
                "",
                insert=(x_label, y),
                font_size="12px",
                font_family="Arial",
            )
            text.add(dwg.tspan(f"{label}: ", fill=self.MUTED_COLOR))
            text.add(dwg.tspan(value, fill="black"))
            dwg.add(text)
            y += line_h

        y += 8
        dwg.add(
            dwg.line(
                start=(x_label, y),
                end=(x_right, y),
                stroke="#cccccc",
                stroke_width=0.6,
            )
        )
        y += 26

        dwg.add(
            dwg.text(
                amount_label or str(_("Total amount")),
                insert=(x_label, y),
                fill=self.MUTED_COLOR,
                font_size="13px",
                font_family="Arial",
            )
        )
        dwg.add(
            dwg.text(
                f"CHF {amount:.2f}",
                insert=(x_value, y),
                fill=self.BRAND_COLOR,
                font_size="20px",
                font_weight="bold",
                font_family="Arial",
            )
        )

    def __draw_invoice_metadata__(self, dwg, invoice: Invoice):
        rows = [
            (_("Invoice no."), "#" + str(invoice.get_reference())),
            (_("Date"), invoice.created_at.strftime("%d %B %Y")),
            (_("Subscription"), invoice.member_subscription.subscription.name),
            (_("Type"), str(invoice.member_subscription.get_type_text())),
        ]
        if invoice.reminder > 0:
            rows.append((_("Reminder"), str(invoice.get_reminder_text())))
        self.__draw_metadata_table__(dwg, rows, invoice.price_decimal())

    def __draw_status_watermark__(self, dwg, invoice: Invoice):
        if invoice.status not in (InvoiceStatusEnum.CANCELED, InvoiceStatusEnum.PAID):
            return
        text = (
            _("** Cancelled **")
            if invoice.status == InvoiceStatusEnum.CANCELED
            else _("** Paid **")
        )
        self.__draw_watermark__(dwg, str(text), fill="red")

    def __draw_watermark__(self, dwg, text: str, fill: str = "red", cy: int = 580):
        cx = self.PAGE_WIDTH / 2
        dwg.add(
            dwg.text(
                text,
                insert=(cx, cy),
                fill=fill,
                font_size="72px",
                font_weight="bold",
                font_family="Arial",
                text_anchor="middle",
                opacity="0.25",
                transform=f"rotate(-20 {cx} {cy})",
            )
        )

    def generate_pdf_blank(self, subscription: Subscription):
        writer = PdfWriter()

        for order, subscription_type in enumerate(
            OrderedDict(SubscriptionTypeEnum.choices)
        ):
            svg_buffer = StringIO()
            with TranslationContext(settings.INVOICE_LANGUAGE):
                price = subscription.get_price_by_type(subscription_type) / 100
                is_suggested = subscription_type == SubscriptionTypeEnum.OTHER

                bill = QRBill(
                    settings.INVOICE_IBAN,
                    creditor=self.__get_creditor__(),
                    debtor=None,
                    amount=None if is_suggested else str(price),
                    language=settings.INVOICE_LANGUAGE,
                    reference_number=None,
                    additional_information=(
                        f"{_('Suggested price')}: {price} CHF" if is_suggested else ""
                    ),
                )
                # A4 page with a white background
                dwg = svgwrite.Drawing(
                    size=A4,
                    viewBox=("0 0 %f %f" % (mm(A4[0]), mm(A4[1]))),
                    debug=False,
                )
                dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill="white"))

                # Draw header
                self.__draw_invoice_logo__(dwg, document_title=str(_("Invoice")))

                rows = [
                    (_("Subscription"), subscription.name),
                    (
                        _("Type"),
                        str(SubscriptionTypeEnum.get_type(subscription_type)),
                    ),
                ]
                self.__draw_metadata_table__(
                    dwg,
                    rows,
                    price,
                    amount_label=str(_("Suggested price")) if is_suggested else None,
                )

                self.__draw_watermark__(
                    dwg, str(_("Transmissible")), fill=self.BRAND_COLOR, cy=540
                )

                # Draw a bill and make it A4
                group = bill.draw_bill(dwg, True)
                bill.transform_to_full_page(dwg, group)

                dwg.write(svg_buffer)

                pdf_reader = PdfReader(self.__svg2Pdf__(svg_buffer))
                writer.append(pdf_reader)
        result = io.BytesIO()
        writer.write(result)
        result.seek(0)

        return result
