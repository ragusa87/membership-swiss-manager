<?php

namespace App\Tests\Bill;

use App\Bill\PdfService;
use App\Entity\Invoice;
use App\Entity\InvoiceStatusEnum;
use App\Entity\Member;
use App\Entity\MemberSubscription;
use App\Entity\Subscription;
use PHPUnit\Framework\TestCase;
use Symfony\Contracts\Translation\TranslatorInterface;
use Symfony\Contracts\Translation\TranslatorTrait;

class PdfServiceTest extends TestCase
{
    public function testGenerate(): void
    {
        $service = $this->getPdfService();
        $response = $service->generate($this->getFullInvoice());

        ob_start();
        $response->send();
        $responseBody = ob_get_contents();
        ob_end_clean();
        // This check that the binary content contains PDF-*, as it's hard to fetch the headers.
        $this->assertNotFalse(strpos($responseBody, 'PDF-'), $responseBody);
    }

    public function testConvert(): void
    {
        $service = $this->getPdfService();

        $invoice = $this->getFullInvoice();

        $qrBill = $service->convert($invoice);
        $this->assertEquals('120000000000000000000000012', $qrBill->getPaymentReference()->getReference());
        $this->assertEquals('CH4431999123000889012', $qrBill->getCreditorInformation()->getIban());
    }

    private function getFullInvoice(): Invoice
    {
        $invoice = new Invoice();
        $invoice->setReference(1);
        $invoice->setPrice(12);
        $invoice->setStatusFromEnum(InvoiceStatusEnum::CREATED);

        $member = new Member();
        $member->setFirstname('Jon');
        $member->setLastname('Doe');
        $member->setAddress('Chemin du Blé');
        $member->setCity('Lausanne');
        $member->setZip(1003);

        $subscription = new Subscription();
        $subscription->setName('2023');

        $memberSubscription = new MemberSubscription();
        $memberSubscription->setPrice(12);
        $memberSubscription->setMember($member);
        $memberSubscription->setSubscription($subscription);

        $invoice->setMemberSubscription($memberSubscription);

        return $invoice;
    }

    private function getPdfService(string $iban = 'CH4431999123000889012'): PdfService
    {
        $translator = new class() implements TranslatorInterface {
            use TranslatorTrait;
        };

        return new PdfService($translator, $iban, '12', 'Association du Vanil', 'Chemin du Vanil', 'Lausanne', 1003, 'CH', 'fr', true);
    }
}
