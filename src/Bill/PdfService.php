<?php

namespace App\Bill;

use App\Entity\Invoice;
use App\Entity\Member;
use App\Entity\MemberSubscription;
use App\Entity\SubscriptionTypeEnum;
use Fpdf\Fpdf;
use Psr\Log\LoggerAwareInterface;
use Psr\Log\LoggerAwareTrait;
use Sprain\SwissQrBill\DataGroup\Element\AdditionalInformation;
use Sprain\SwissQrBill\DataGroup\Element\CombinedAddress;
use Sprain\SwissQrBill\DataGroup\Element\CreditorInformation;
use Sprain\SwissQrBill\DataGroup\Element\PaymentAmountInformation;
use Sprain\SwissQrBill\DataGroup\Element\PaymentReference;
use Sprain\SwissQrBill\PaymentPart\Output\FpdfOutput\FpdfOutput;
use Sprain\SwissQrBill\QrBill;
use Sprain\SwissQrBill\Reference\QrPaymentReferenceGenerator;
use Sprain\SwissQrBill\Reference\RfCreditorReferenceGenerator;
use Symfony\Component\HttpFoundation\StreamedResponse;
use Symfony\Contracts\Translation\TranslatorInterface;

class PdfService implements LoggerAwareInterface
{
    use LoggerAwareTrait;

    public function __construct(
        protected TranslatorInterface $translator,
        protected string $iban,
        protected string $customerIdentificationNumber,
        protected string $addressName,
        protected string $addressStreet,
        protected string $addressCity,
        protected string $addressZip,
        protected string $addressCountry,
        protected string $language,
        protected bool $printable,
    ) {
    }

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
            $this->logger?->warning($invalidArgumentException);
        }

        // Add payment amount information
        // What amount is to be paid?
            $qrBill->setPaymentAmountInformation(
                PaymentAmountInformation::create(
                    'CHF',
                    // Supporters can choose the amount.
                    SubscriptionTypeEnum::SUPPORTER !== $invoice->getMemberSubscription()->getTypeEnum() ? $invoice->getPrice() / 100 : null
                ));

        // Add payment reference
        // This is what you will need to identify incoming payments.
        $this->addReference($qrBill, $invoice);

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

    public function generate(Invoice ...$invoices): StreamedResponse
    {
        $fpdf = new Fpdf('P', 'mm', 'A4');
        $fpdf->SetCreator('membership-swiss-manager');
        $fpdf->SetTitle(1 == count($invoices) ? 'Invoice '.$invoices[0]->getReference() : 'Invoices');
        foreach ($invoices as $invoice) {
            $fpdf->AddPage();
            $output = new FpdfOutput($this->convert($invoice), $this->language, $fpdf);
            $this->insertHeader($fpdf, $invoice);
            // @phpstan-ignore-next-line
            $output
                ->setPrintable($this->printable)
                ->getPaymentPart();
        }

        return new StreamedResponse(function () use ($fpdf) {
            $fpdf->Output('I', sprintf('Invoices-%s.pdf', date('Y-m-d-His')));
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

        return $this->translator->trans('pdf.invoice.name', [
            '{{ name }}' => $subscription->getName(),
            '{{ type }}' => $this->translator->trans('subscription_type_enum.'.$invoice->getMemberSubscription()->getTypeEnum()->value),
        ]);
    }

    protected function insertHeader(Fpdf $fpdf, Invoice $invoice)
    {
        $fpdf->SetFont('Arial', 'B', 16);
        $fpdf->Write(0, iconv('utf-8', 'ISO-8859-2', $this->addressName));
        $fpdf->Ln(5);

        $fpdf->SetFont('Arial', '', 10);

        $fpdf->Write(0, iconv('utf-8', 'ISO-8859-2', $this->getInvoiceName($invoice)));
        $fpdf->Ln(10);

        $member = $invoice->getMemberSubscription()->getMember();
        $fpdf->Write(0, iconv('utf-8', 'ISO-8859-2', $member->getFullname()));
        $fpdf->Ln(5);
        $fpdf->Write(0, iconv('utf-8', 'ISO-8859-2', $member->getFullAddressLine1()));
        $fpdf->Ln(5);
        $fpdf->Write(0, iconv('utf-8', 'ISO-8859-2', $member->getFullAddressLine2()));
        $fpdf->Ln(5);
        $fpdf->Write(0, iconv('utf-8', 'ISO-8859-2', $member->getEmail()));
        $fpdf->Ln(5);
        $fpdf->Write(0, iconv('utf-8', 'ISO-8859-2', $member->getPhone()));
        $fpdf->Ln(5);
        if ($member->getChildren()->count() > 0) {
            $fpdf->Write(0, iconv('utf-8', 'ISO-8859-2', $this->translator->trans('With: ')));
            $fpdf->Ln(5);
            foreach ($member->getChildren() as $child) {
                $fpdf->Write(0, iconv('utf-8', 'ISO-8859-2', $child->getFullname()));
                $fpdf->Ln(5);
            }
        }

        $fpdf->Ln(15);
        $fpdf->Write(0, iconv('utf-8', 'ISO-8859-2', $this->translator->trans('pdf.invoice.ref', ['{{ ref }}' => $invoice->getReference()])));
        $fpdf->Ln(5);

        $priceMember = MemberSubscription::getPriceByType(SubscriptionTypeEnum::MEMBER);
        $priceSupporter = MemberSubscription::getPriceByType(SubscriptionTypeEnum::SUPPORTER);
        $fpdf->Write(0, iconv('utf-8', 'ISO-8859-2', $this->translator->trans('pdf.message', [
            '{{ priceMember }}' => $priceMember / 100,
            '{{ priceSupporter }}' => $priceSupporter / 100,
        ])));
    }

    private function isIbanCompatibleWithQRCodeReference()
    {
        $iban = str_replace(' ', '', $this->iban);
        $qrIid = substr($iban, 4, 5);

        return (int) $qrIid >= 30000 && (int) $qrIid <= 31999;
    }

    private function addReference(QrBill $qrBill, Invoice $invoice): void
    {
        if ($this->isIbanCompatibleWithQRCodeReference()) {
            if ('' === trim($this->customerIdentificationNumber)) {
                throw new \InvalidArgumentException('You must configure the customer identification number');
            }
            $referenceNumber = QrPaymentReferenceGenerator::generate(
                $this->customerIdentificationNumber,
                $invoice->getReference()
            );
            $qrBill->setPaymentReference(
                PaymentReference::create(
                    PaymentReference::TYPE_QR,
                    $referenceNumber
                ));

            return;
        }
        $referenceNumber = RfCreditorReferenceGenerator::generate(
            str_pad($invoice->getReference(), 21, '0', STR_PAD_LEFT)
        );
        $qrBill->setPaymentReference(
            PaymentReference::create(
                PaymentReference::TYPE_SCOR,
                $referenceNumber
            ));
    }
}
