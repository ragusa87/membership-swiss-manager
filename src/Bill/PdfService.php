<?php

namespace App\Bill;

use App\Entity\Invoice;
use App\Entity\Member;
use App\Entity\SubscriptionTypeEnum;
use Fpdf\Fpdf;
use Sprain\SwissQrBill\DataGroup\Element\AdditionalInformation;
use Sprain\SwissQrBill\DataGroup\Element\CombinedAddress;
use Sprain\SwissQrBill\DataGroup\Element\CreditorInformation;
use Sprain\SwissQrBill\DataGroup\Element\PaymentAmountInformation;
use Sprain\SwissQrBill\DataGroup\Element\PaymentReference;
use Sprain\SwissQrBill\PaymentPart\Output\FpdfOutput\FpdfOutput;
use Sprain\SwissQrBill\QrBill;
use Sprain\SwissQrBill\Reference\QrPaymentReferenceGenerator;
use Symfony\Component\HttpFoundation\StreamedResponse;

class PdfService
{
    protected string $customerIdentificationNumber = '210000';
    protected string $iban = 'CH4431999123000889012';
    protected string $language = 'en';
    protected string $addressName = 'Association Voisins Du Vanil';
    protected string $addressStreet = 'Chemin du Vanil';
    protected string $addressCity = 'Lausanne';
    protected string $addressZip = '1006';
    protected string $addressCountry = 'CH';

    public function convert(Invoice $invoice): QrBill
    {
        if (null === $invoice->getPrice()) {
            throw new \InvalidArgumentException('Invoice must have a price');
        }

        if (null === $invoice->getMemberSubscription()) {
            throw new \InvalidArgumentException('Invoice must have a subscription');
        }

        if (null === $invoice->getMemberSubscription()->getMember()) {
            throw new \InvalidArgumentException("Invoice's subscription must have a member");
        }

        if (null === $invoice->getMemberSubscription()->getSubscription()) {
            throw new \InvalidArgumentException("Invoice's subscription is invalid");
        }

        $qrBill = QrBill::create();
        $qrBill->setCreditor(
            CombinedAddress::create(
                $this->addressName,
                $this->addressStreet,
                sprintf('%s %s', $this->addressZip, $this->addressCity),
                $this->addressCountry
            ));

        $qrBill->setCreditorInformation(
            CreditorInformation::create(
                $this->iban // This is a special QR-IBAN. Classic IBANs will not be valid here.
            ));

        $member = $invoice->getMemberSubscription()?->getMember();

        // Who has to pay the invoice?
        try {
            $qrBill->setUltimateDebtor(
                $this->memberToAddress($member)
            );
        } catch (\InvalidArgumentException $invalidArgumentException) {
            // TODO log
        }

        // Add payment amount information
        // What amount is to be paid?
        $qrBill->setPaymentAmountInformation(
            PaymentAmountInformation::create(
                'CHF',
                $invoice->getPrice() / 100
            ));

        // Add payment reference
        // This is what you will need to identify incoming payments.
        $referenceNumber = QrPaymentReferenceGenerator::generate(
            $this->customerIdentificationNumber,  // You receive this number from your bank (BESR-ID). Unless your bank is PostFinance, in that case use NULL.
            $invoice->getReference()// A number to match the payment with your internal data, e.g. an invoice number
        );

        $qrBill->setPaymentReference(
            PaymentReference::create(
                PaymentReference::TYPE_QR,
                $referenceNumber
            ));

        // Optionally, add some human-readable information about what the bill is for.
        $qrBill->setAdditionalInformation(
            AdditionalInformation::create(
                $this->getInvoiceName($invoice)
            )
        );

        if (false === $qrBill->isValid()) {
            $error = $qrBill->getViolations()->get(0);
            throw new \RuntimeException(sprintf('Invalid bill, %s', $error));
        }

        return $qrBill;
    }

    public function generate(Invoice $invoice): StreamedResponse
    {
        $fpdf = new Fpdf('P', 'mm', 'A4');
        $fpdf->AddPage();
        $output = new FpdfOutput($this->convert($invoice), $this->language, $fpdf);

        $this->insertHeader($fpdf, $invoice);
        $output
            ->setPrintable(false)
            ->getPaymentPart();

        return new StreamedResponse(function () use ($fpdf, $invoice) {
            $fpdf->Output('I', sprintf('Invoice-%s.pdf', $invoice->getReference()));
        });
    }

    protected function memberToAddress(Member $member): CombinedAddress
    {
        if (null == $member->getFullAddressLine2() || null === $member->getFullAddressLine1()) {
            throw new \InvalidArgumentException('Not able to convert address');
        }

        // StructuredAddress is not worth it
        return CombinedAddress::create(
            $member->getFullname(),
            $member->getFullAddressLine1(),
            $member->getFullAddressLine2(),
            $member->getCountry() ?? 'CH',
        );
    }

    protected function getInvoiceName(Invoice $invoice): string
    {
        $subscription = $invoice->getMemberSubscription()->getSubscription();

        $type = $this->translateSubscriptionType($invoice->getMemberSubscription()->getTypeEnum());

        return sprintf('Cotisation %s %s', $type, $subscription->getName());
    }

    protected function insertHeader(Fpdf $fpdf, Invoice $invoice)
    {
        $fpdf->SetFont('Arial', 'B', 16);
        $fpdf->Write(0, $this->addressName);
        $fpdf->Ln(5);

        $fpdf->SetFont('Arial', '', 10);

        $fpdf->Write(0, $this->getInvoiceName($invoice));
        $fpdf->Ln(10);

        $member = $invoice->getMemberSubscription()->getMember();
        $fpdf->Write(0, $member->getFullname());
        $fpdf->Ln(5);
        $fpdf->Write(0, $member->getFullAddressLine1());
        $fpdf->Ln(5);
        $fpdf->Write(0, $member->getFullAddressLine2());
        $fpdf->Ln(5);
        $fpdf->Write(0, $member->getEmail());
        $fpdf->Ln(5);
        $fpdf->Write(0, $member->getPhone());
        $fpdf->Ln(5);
        if ($member->getChildren()->count() > 0) {
            $fpdf->Write(0, 'Avec:');
            $fpdf->Ln(5);
            foreach ($member->getChildren() as $child) {
                $fpdf->Write(0, $child->getFullname());
                $fpdf->Ln(5);
            }
        }

        $fpdf->Ln(15);
        $fpdf->Write(0, iconv('utf-8', 'ISO-8859-2', 'Facture Numéro: '.$invoice->getReference()));
        $fpdf->Ln(5);

        $fpdf->Write(0, iconv('utf-8', 'ISO-8859-2', 'Cotisation: 50 CHF par carré, 30 CHF Membres sympatisants'));
    }

    protected function translateSubscriptionType(SubscriptionTypeEnum $getTypeEnum)
    {
        switch ($getTypeEnum) {
            case SubscriptionTypeEnum::MEMBER:
                return 'membre';
            case SubscriptionTypeEnum::SUPPORTER:
                return 'sympatisant';
        }
    }
}
