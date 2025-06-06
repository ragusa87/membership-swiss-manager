import io
from collections import OrderedDict
from io import StringIO
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
    def __init__(self):
        self.logo_letter = "V"
        pass

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
            pos = self.__draw_invoice_logo__(dwg)
            self.__draw_invoice_header__(dwg, pos, invoice)

            # Draw a bill and make it A4
            group = bill.draw_bill(dwg, True)
            bill.transform_to_full_page(dwg, group)

            dwg.write(svg_buffer)

            return self.__svg2Pdf__(svg_buffer)

    def __draw_invoice_logo__(self, dwg):
        pos = Position(20, 20)

        # Add logo placeholder
        dwg.add(
            dwg.rect(
                insert=pos.as_tuple(), size=("80px", "80px"), fill="black", rx=5, ry=5
            )
        )
        pos.move(20, 60)
        dwg.add(
            dwg.text(
                self.logo_letter,
                insert=pos.as_tuple(),
                fill="white",
                font_size="58px",
                font_weight="bold",
                font_family="Arial",
            )
        )

        # Add title
        pos.set(120, 70)
        dwg.add(
            dwg.text(
                settings.CREDITOR_NAME,
                insert=pos.as_tuple(),
                fill="black",
                font_size="24px",
                font_weight="bold",
                font_family="Arial",
            )
        )

        return pos

    def __draw_invoice_header__(self, dwg, pos, invoice: Invoice):
        # Add invoice title (member)
        pos.set(20, 164)

        dwg.add(
            dwg.text(
                invoice.member_subscription.member.get_fullname(),
                insert=pos.as_tuple(),
                fill="black",
                font_size="24px",
                font_weight="bold",
                font_family="Arial",
            )
        )
        pos.move(0, 24)

        for related_subscription in MemberSubscription.objects.filter(
            parent=invoice.member_subscription
        ):
            dwg.add(
                dwg.text(
                    "& " + related_subscription.member.get_fullname(),
                    insert=pos.as_tuple(),
                    fill="black",
                    font_size="24px",
                    font_weight="bold",
                    font_family="Arial",
                )
            )
            pos.move(0, 24)

        name = (
            ""
            + str(invoice.member_subscription.get_type_text())
            + " "
            + str(invoice.member_subscription.subscription.name)
        )
        dwg.add(
            dwg.text(
                name,
                insert=pos.as_tuple(),
                fill="black",
                font_size="14px",
                font_family="Arial",
            )
        )
        pos.move(0, 24)

        # Add date and invoice number
        date = invoice.created_at.strftime("%d %B %Y")
        dwg.add(
            dwg.text(
                date,
                insert=pos.as_tuple(),
                fill="black",
                font_size="14px",
                font_family="Arial",
            )
        )
        pos.move(0, 24)
        dwg.add(
            dwg.text(
                "# " + str(invoice.get_reference()),
                insert=pos.as_tuple(),
                fill="black",
                font_size="14px",
                font_family="Arial",
            )
        )
        pos.move(0, 14)

        if invoice.reminder > 0:
            dwg.add(
                dwg.text(
                    invoice.get_reminder_text(),
                    insert=pos.as_tuple(),
                    fill="black",
                    font_size="14px",
                    font_family="Arial",
                )
            )
            pos.move(0, 14)

        if invoice.status in [InvoiceStatusEnum.CANCELED, InvoiceStatusEnum.PAID]:
            pos.move(0, 20)
            dwg.add(
                dwg.text(
                    _("** Cancelled **")
                    if invoice.status == InvoiceStatusEnum.CANCELED
                    else _("** Paid **"),
                    insert=pos.as_tuple(),
                    fill="red",
                    font_size="28px",
                    font_family="Arial",
                )
            )
            pos.move(0, 28)

        return pos

    def generate_pdf_blank(self, subscription: Subscription):
        writer = PdfWriter()

        for order, subscription_type in enumerate(
            OrderedDict(SubscriptionTypeEnum.choices)
        ):
            svg_buffer = StringIO()
            with TranslationContext(settings.INVOICE_LANGUAGE):
                price_info = ""
                amount = str(subscription.get_price_by_type(subscription_type) / 100)

                if subscription_type == SubscriptionTypeEnum.OTHER:
                    price_info = _("Suggested price") + ": " + amount + " CHF"
                    amount = None

                infos = (
                    _("Transmissible")
                    + ": "
                    + SubscriptionTypeEnum.get_type(subscription_type)
                )
                infos += "\n" + price_info + "\n" + subscription.name

                bill = QRBill(
                    settings.INVOICE_IBAN,
                    creditor=self.__get_creditor__(),
                    debtor=None,
                    amount=amount,
                    language=settings.INVOICE_LANGUAGE,
                    reference_number=None,
                    additional_information=price_info,
                )
                # A4 page with a white background
                dwg = svgwrite.Drawing(
                    size=A4,
                    viewBox=("0 0 %f %f" % (mm(A4[0]), mm(A4[1]))),
                    debug=False,
                )
                dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill="white"))

                # Draw header
                pos = self.__draw_invoice_logo__(dwg)

                # Draw infos
                # Add subscription infos
                pos.set(20, 164)
                dwg.add(
                    dwg.text(
                        (
                            SubscriptionTypeEnum.get_type(subscription_type)
                            + " "
                            + subscription.name
                        ).capitalize(),
                        insert=pos.as_tuple(),
                        fill="black",
                        font_size="24px",
                        font_weight="bold",
                        font_family="Arial",
                    )
                )
                pos.move(0, 24)
                dwg.add(
                    dwg.text(
                        price_info,
                        insert=pos.as_tuple(),
                        fill="black",
                        font_size="14px",
                        font_family="Arial",
                    )
                )
                pos.move(0, 24)
                dwg.add(
                    dwg.text(
                        _("Transmissible"),
                        insert=pos.as_tuple(),
                        fill="black",
                        font_size="14px",
                        font_family="Arial",
                    )
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
