import io

import pandas as pd
from io import BytesIO
from .format import EXPECTED_HEADERS
from ..models import MemberSubscription, Subscription
from ..templatetags.custom_filters import format_price


class CsvExporter:
    def __init__(self, subscription: Subscription):
        self.__member_subscriptions__ = MemberSubscription.list_for_dashboard(
            subscription
        )

    def export(self, extension: str) -> io.BytesIO:
        data_list = []
        headers = EXPECTED_HEADERS + ["factures"]
        for subscription in self.__member_subscriptions__:
            data = {
                "id": subscription.pk,
                "membres": ", ".join(
                    [subscription.member.get_fullname()]
                    + [
                        child.member.get_fullname()
                        for child in subscription.children.all()
                    ]
                ),
                "type d'inscription": subscription.get_type_text(),
                "prix": subscription.price,
                "Montant Dû": subscription.get_due_amount(),
                "factures": ", ".join(
                    [
                        f"{i.get_status_text()} {format_price(i.price)}"
                        for i in subscription.invoices.all()
                    ]
                ),
            }
            data_list.append(data)

        df = pd.DataFrame(data_list)
        output = BytesIO()

        if extension.lower() == "csv":
            df.to_csv(output, index=False)
            output.seek(0)
            return output

        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, header=headers)
            workbook = writer.book
            worksheet = writer.sheets["Sheet1"]

            red_fill = workbook.add_format({"bg_color": "#FF9999"})
            worksheet.conditional_format(
                "A2:Z2000",
                {"type": "formula", "criteria": "=$E2>0", "format": red_fill},
            )
        output.seek(0)

        return output
