<?php

namespace App\Helper;

use App\Entity\InvoiceStatusEnum;
use App\Entity\MemberSubscription;
use PhpOffice\PhpSpreadsheet\IOFactory;
use PhpOffice\PhpSpreadsheet\Spreadsheet;
use PhpOffice\PhpSpreadsheet\Style\Color;
use PhpOffice\PhpSpreadsheet\Style\ConditionalFormatting\Wizard;
use PhpOffice\PhpSpreadsheet\Worksheet\Worksheet;
use Symfony\Component\HttpFoundation\StreamedResponse;
use Symfony\Component\Routing\RouterInterface;
use Symfony\Contracts\Translation\TranslatorInterface;

class MemberSubscriptionXlsExporter
{
    public function __construct(protected RouterInterface $router, protected TranslatorInterface $translator)
    {
    }

    /**
     * @param array<MemberSubscription> $memberSubscriptions
     */
    protected function export(array $memberSubscriptions): Spreadsheet
    {
        $spreadsheet = new Spreadsheet();
        $spreadsheet->setActiveSheetIndex(0);
        $this->fill($spreadsheet->getActiveSheet(), $memberSubscriptions);

        return $spreadsheet;
    }

    /**
     * @param array<MemberSubscription> $memberSubscriptions
     */
    public function exportToXlsx(array $memberSubscriptions): StreamedResponse
    {
        $response = new StreamedResponse(function () use ($memberSubscriptions) {
            $spreadsheet = $this->export($memberSubscriptions);
            $writer = IOFactory::createWriter($spreadsheet, IOFactory::WRITER_XLSX);
            $writer->save('php://output');
        });
        $response->headers->set('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
        $response->headers->set('Content-Disposition', 'inline');

        return $response;
    }

    /**
     * @param array<MemberSubscription> $memberSubscriptions
     */
    public function exportToHtml(array $memberSubscriptions): StreamedResponse
    {
        $response = new StreamedResponse(function () use ($memberSubscriptions) {
            $spreadsheet = $this->export($memberSubscriptions);
            $writer = IOFactory::createWriter($spreadsheet, IOFactory::WRITER_HTML);
            $writer->save('php://output');
        });
        $response->headers->set('Content-Type', 'text/html');
        $response->headers->set('Content-Disposition', 'inline');

        return $response;
    }

    /**
     * @param array<MemberSubscription> $memberSubscriptions
     */
    protected function fill(Worksheet $workSheet, array $memberSubscriptions): void
    {
        $index = 1;
        $workSheet->setCellValue('A'.$index, 'id');
        $workSheet->setCellValue('B'.$index, $this->translator->trans('Members'));
        $workSheet->setCellValue('C'.$index, $this->translator->trans('subscription_type_enum.label'));
        $workSheet->setCellValue('D'.$index, $this->translator->trans('Price'));
        $workSheet->setCellValue('E'.$index, $this->translator->trans('Due Amount'));

        foreach ($memberSubscriptions as $memberSubscription) {
            ++$index;

            $workSheet->setCellValue('A'.$index, $memberSubscription->getId());
            $workSheet->getCell('A'.$index)->getHyperlink()->setUrl($this->router->generate('view_membersubscription_by_id', ['id' => $memberSubscription->getId()], RouterInterface::ABSOLUTE_URL));

            $workSheet->setCellValue('B'.$index, $this->getMemberNames($memberSubscription));
            $workSheet->getColumnDimension('B')->setAutoSize(true);
            $workSheet->getStyle('A'.$index.':E'.$index)->getFont()->setBold($memberSubscription->getDueAmount() > 0);

            $workSheet->setCellValue('C'.$index, $memberSubscription->getTypeEnum()->value);
            $workSheet->setCellValue('D'.$index, number_format($memberSubscription->getPrice() / 100.0, 2));
            $workSheet->setCellValue('E'.$index, number_format($memberSubscription->getDueAmount() / 100.0, 2));
            $this->addInvoices($workSheet, $memberSubscription, $index, 'F');
        }

        // Add sums
        ++$index;
        $workSheet->setCellValue('D'.$index, '=SUM(D1:D'.($index - 1).')');
        $workSheet->setCellValue('E'.$index, '=SUM(E1:E'.($index - 1).')');

        $this->applyConditionalFormatting($workSheet, 'E', $index);
    }

    private function getMemberNames(MemberSubscription $memberSubscription): string
    {
        $names = [$memberSubscription->getMember()->getFullname()];
        foreach ($memberSubscription->getMember()->getChildren() as $child) {
            $names[] = $child->getFullname();
        }

        return implode(', ', $names);
    }

    private function applyConditionalFormatting(Worksheet $workSheet, string $letter, int $index): void
    {
        $wizardFactory = new Wizard($letter.'2:'.$letter.($index - 1));

        foreach ([[0, 'greaterThan', Color::COLOR_RED], [0, 'lessThanOrEqual', Color::COLOR_GREEN]] as $rule) {
            list($value, $method, $color) = $rule;

            $wizard = $wizardFactory->newRule(Wizard::CELL_VALUE);
            $wizard->{$method}($value);

            $style = $wizard->getStyle();
            $style->getFont()->getColor()->setARGB($color);
            $style->getFont()->setBold(true);
            $wizard->setStyle($style);

            $conditionalStyles = $workSheet->getStyle($wizard->getCellRange())->getConditionalStyles();
            $conditionalStyles[] = $wizard->getConditional();
            $workSheet->getStyle($wizard->getCellRange())->setConditionalStyles($conditionalStyles);
        }
    }

    private function addInvoices(Worksheet $workSheet, MemberSubscription $memberSubscription, int $index, string $letter): void
    {
        $invoices = $memberSubscription->getInvoices();
        $nextLetter = $letter;
        foreach ($invoices as $invoice) {
            if (InvoiceStatusEnum::CANCELED === $invoice->getStatusAsEnum()) {
                continue;
            }

            $value = sprintf('%s(%s)', $invoice->getStatusAsEnum()->value, $invoice->getFormattedPrice());

            $cell = $nextLetter.$index;
            $workSheet->setCellValue($cell, $value);
            $workSheet->getCell($cell)->getHyperlink()->setUrl($this->router->generate('view_invoice_by_id', ['id' => $invoice->getId()], RouterInterface::ABSOLUTE_URL));
            $nextLetter = chr(ord($letter) + 1);
        }
    }
}
