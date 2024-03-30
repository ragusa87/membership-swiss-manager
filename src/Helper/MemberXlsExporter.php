<?php

namespace App\Helper;

use App\Entity\Member;
use App\Entity\MemberSubscription;
use App\Entity\Subscription;
use PhpOffice\PhpSpreadsheet\Cell\DataType;
use PhpOffice\PhpSpreadsheet\IOFactory;
use PhpOffice\PhpSpreadsheet\Spreadsheet;
use PhpOffice\PhpSpreadsheet\Worksheet\Worksheet;
use Psr\Log\LoggerInterface;

class MemberXlsExporter
{
    public function __construct(protected AddressConverterService $addressConverterService, protected ?LoggerInterface $logger = null)
    {
    }

    /**
     * @param array<int, MemberSubscription> $memberSubscriptions
     *
     * @throws \PhpOffice\PhpSpreadsheet\Writer\Exception
     */
    public function exportToFile(Subscription $subscription, array $memberSubscriptions, string $filename): void
    {
        $file = fopen($filename, 'w');
        if (false === $file) {
            throw new \RuntimeException('Could not open file '.$filename);
        }
        $spreadsheet = $this->export($subscription, $memberSubscriptions);
        $writer = IOFactory::createWriter($spreadsheet, IOFactory::WRITER_XLSX);
        $writer->save($file);
        fclose($file);
    }

    /**
     * @param array<int, MemberSubscription> $memberSubscription
     */
    protected function export(Subscription $subscription, array $memberSubscription = null): Spreadsheet
    {
        $spreadsheet = new Spreadsheet();
        $sheet = $spreadsheet->getActiveSheet();
        $sheet->setTitle('Subscription '.$subscription->getName());
        $this->addHeaders($sheet);
        $index = 2;
        foreach (($memberSubscription ?? $subscription->getSubscription()) as $subscription) {
            $member = $subscription->getMember();

            $this->addMemberToSheet($sheet, $member, $subscription, $index);
            ++$index;

            foreach ($member->getChildren() as $child) {
                $this->addMemberToSheet($sheet, $child, $subscription, $index);
                ++$index;
            }
        }

        return $spreadsheet;
    }

    private function addHeaders(Worksheet $sheet): void
    {
        $sheet->setCellValue('A1', MemberXlsImporter::HEADER_NAME_DIRTY);
        $sheet->setCellValue('B1', MemberXlsImporter::HEADER_ADDRESS_DIRTY);
        $sheet->setCellValue('C1', MemberXlsImporter::HEADER_CITY_DIRTY);
        $sheet->setCellValue('D1', MemberXlsImporter::HEADER_EMAIL_DIRTY);
        $sheet->setCellValue('E1', MemberXlsImporter::HEADER_PHONE_DIRTY);
        $sheet->setCellValue('F1', MemberXlsImporter::HEADER_PARENT);
        $sheet->setCellValue('G1', MemberXlsImporter::HEADER_SUBSCRIPTION_TYPE);
    }

    private function addMemberToSheet(Worksheet $sheet, ?Member $member, MemberSubscription $subscription, int $index): void
    {
        $sheet->setCellValue('A'.$index, $member->getFullname());
        $sheet->setCellValue('B'.$index, $member->getFullAddressLine1());
        $sheet->setCellValue('C'.$index, $member->getFullAddressLine2());
        $sheet->setCellValue('D'.$index, $member->getEmail());
        $sheet->setCellValueExplicit('E'.$index, $member->getPhone(), DataType::TYPE_STRING);
        $sheet->setCellValue('F'.$index, $member->getParent()?->getFullname());
        $sheet->setCellValue('G'.$index, $subscription->getTypeEnum()->value);
    }
}
