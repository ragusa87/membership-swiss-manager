<?php

namespace App\Helper;

use App\Entity\Invoice;
use App\Entity\InvoiceStatusEnum;
use App\Entity\MemberSubscription;
use Doctrine\Persistence\ManagerRegistry;
use Doctrine\Persistence\ObjectManager;
use Psr\Log\LoggerAwareInterface;
use Psr\Log\LoggerAwareTrait;
use Psr\Log\NullLogger;

class InvoiceHelper implements LoggerAwareInterface
{
    use LoggerAwareTrait;

    public function __construct(protected ManagerRegistry $managerRegistry)
    {
    }

    protected function getManagerInvoices(): ObjectManager
    {
        return $this->managerRegistry->getManagerForClass(Invoice::class);
    }

    /**
     * @param array<MemberSubscription> $memberSubscriptions
     *
     * @return array<Invoice>
     */
    public function generate(array $memberSubscriptions): array
    {
        $createdInvoices = [];

        foreach ($memberSubscriptions as $memberSubscription) {
            if (0 == $memberSubscription->getDueAmount() || false === $memberSubscription->isActive()) {
                continue;
            }

            if (0 === $memberSubscription->getInvoices()->count()) {
                $this->logger()->info('Generating first invoice for subscription '.$memberSubscription->getId());
                $invoice = $memberSubscription->generateNewInvoice();
                $this->getManagerInvoices()->persist($invoice);
                $createdInvoices[] = $invoice;

                continue;
            }

            foreach ($memberSubscription->getInvoices() as $invoice) {
                if (in_array($invoice->getStatusAsEnum(), [InvoiceStatusEnum::PAID, InvoiceStatusEnum::CANCELED, InvoiceStatusEnum::CREATED], true)) {
                    continue;
                }
                $createdInvoices[] = $this->generateReminder($invoice);
            }

            // If there is no open invoices, but still money to be paid, reopen a new bill
            if (0 === count($this->invoicesBySubscriptionAndStatuses([$memberSubscription], [InvoiceStatusEnum::CREATED, InvoiceStatusEnum::PENDING]))) {
                $this->logger()->info('Generating new invoice for subscription '.$memberSubscription->getId());

                $maxReminder = 0;
                foreach ($memberSubscription->getInvoices() as $invoice) {
                    $maxReminder = max($maxReminder, $invoice->getReminder());
                }

                $invoice = $memberSubscription->generateNewInvoice();
                $invoice->setReminder($maxReminder + 1);
                $this->getManagerInvoices()->persist($invoice);
                $createdInvoices[] = $invoice;
            }
        }
        $this->getManagerInvoices()->flush();
        $createdInvoices = array_filter($createdInvoices);

        return $createdInvoices;
    }

    public function generateReminder(Invoice $invoice, bool $flush = false): ?Invoice
    {
        if (null === $invoice->getMemberSubscription()) {
            $this->logger()->warning('Missing member subscription for invoice', ['invoice_id' => $invoice->getId()]);

            return null;
        }

        if (InvoiceStatusEnum::PENDING !== $invoice->getStatusAsEnum()) {
            $this->logger()->debug('Only pending invoice can have reminders', [
                'invoice_id' => $invoice->getId(),
                'invoice_status' => $invoice->getStatus(),
                'invoice_updated' => $invoice->getUpdatedAt(),
            ]);

            return null;
        }

        if ($invoice->getUpdatedAt() >= new \DateTime('30 days ago')) {
            $this->logger()->debug('Skipping reminder generation for invoice, as last reminder was done recently', [
                'invoice_id' => $invoice->getId(),
                'invoice_updated' => $invoice->getUpdatedAt(),
                'invoice_status' => $invoice->getStatus(),
                'invoice_reminder' => $invoice->getReminder(),
            ]);

            return null;
        }

        $this->logger()->info('Generating reminder', [
            'member_subscription' => $invoice->getMemberSubscription()->getId(),
            'invoice_id' => $invoice->getId(),
            'invoice_created' => $invoice->getCreatedAt(),
            'invoice_status' => $invoice->getStatus(),
            'invoice_reminder' => $invoice->getReminder(),
            'reminder' => $invoice->getReminder() + 1,
        ]);

        $reminder = $invoice->getMemberSubscription()->generateNewInvoice();
        $reminder->setReminder($invoice->getReminder() + 1);
        // The "old" invoice is not to be paid anymore
        $invoice->setStatusFromEnum(InvoiceStatusEnum::CANCELED);

        $this->getManagerInvoices()->persist($reminder);
        $this->getManagerInvoices()->persist($invoice);

        if($flush){
            $this->getManagerInvoices()->flush();
        }

        return $reminder;
    }

    public function logger(): BufferedLogger
    {
        static $logger = new BufferedLogger();
        $logger->setLogger($this->logger ??= new NullLogger());

        return $logger;
    }

    /**
     * @param array<MemberSubscription> $memberSubscriptions
     *
     * @return array<Invoice>
     */
    public function createdInvoices(array $memberSubscriptions): array
    {
        return $this->invoicesBySubscriptionAndStatuses($memberSubscriptions, [InvoiceStatusEnum::CREATED]);
    }

    /**
     * @param MemberSubscription[] $memberSubscriptions
     * @param InvoiceStatusEnum[]  $statuses
     *
     * @return Invoice[]
     */
    public function invoicesBySubscriptionAndStatuses(array $memberSubscriptions, array $statuses): array
    {
        $invoices = [];
        foreach ($memberSubscriptions as $memberSubscription) {
            foreach ($memberSubscription->getInvoices() as $invoice) {
                if (in_array($invoice->getStatusAsEnum(), $statuses, true)) {
                    $invoices[] = $invoice;
                }
            }
        }

        return $invoices;
    }

    public function generateSingleInvoice(MemberSubscription $memberSubscription): Invoice
    {
        if ($memberSubscription->getDueAmount() <= 0) {
            throw new \RuntimeException('No due amount');
        }

        $reminder = 0;
        $hasInvoices = false;
        foreach ($memberSubscription->getInvoices() as $invoice) {
            $reminder = max($reminder, $invoice->getReminder());
            $hasInvoices = true;
        }

        if ($hasInvoices) {
            ++$reminder;
        }

        $invoice = $memberSubscription->generateNewInvoice();
        $invoice->setReminder($reminder);

        $this->getManagerInvoices()->persist($invoice);
        $this->getManagerInvoices()->flush();

        return $invoice;
    }
}
