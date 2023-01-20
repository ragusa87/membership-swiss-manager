<?php

namespace App\Helper;

use App\Entity\Invoice;
use App\Entity\InvoiceStatusEnum;
use App\Entity\MemberSubscription;
use Doctrine\Persistence\ManagerRegistry;
use Doctrine\Persistence\ObjectManager;
use Psr\Log\LoggerAwareInterface;
use Psr\Log\LoggerAwareTrait;
use Psr\Log\LoggerInterface;
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
            if (0 == $memberSubscription->getDueAmount()) {
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
                if (InvoiceStatusEnum::PAID === $invoice->getStatusAsEnum()) {
                    continue;
                }

                if (InvoiceStatusEnum::PENDING === $invoice->getStatusAsEnum()) {
                    continue;
                }

                if ($invoice->getCreatedAt() < new \DateTime('30 days ago 00:00:00')) {
                    // Create a reminder
                    $this->logger()->info('Generating reminder', [
                        'subscription' => $memberSubscription->getId(),
                        'invoice_id' => $invoice->getId(),
                        'invoice_created' => $invoice->getCreatedAt(),
                        'invoice_status' => $invoice->getStatus(),
                        'invoice_reminder' => $invoice->getReminder(),
                        'reminder' => $invoice->getReminder() + 1,
                    ]);

                    $reminder = $memberSubscription->generateNewInvoice();
                    $reminder->setReminder($invoice->getReminder() + 1);
                    // The "old" invoice is not to be paid anymore
                    $invoice->setStatusFromEnum(InvoiceStatusEnum::PENDING);
                    $this->getManagerInvoices()->persist($reminder);
                    $this->getManagerInvoices()->persist($invoice);
                    $createdInvoices[] = $reminder;
                }
            }
        }
        $this->getManagerInvoices()->flush();

        return $createdInvoices;
    }

    private function logger(): LoggerInterface
    {
        return $this->logger ?? new NullLogger();
    }

    /**
     * @param array<MemberSubscription> $memberSubscriptions
     *
     * @return array<Invoice>
     */
    public function createdInvoices(array $memberSubscriptions): array
    {
        $invoices = [];
        foreach ($memberSubscriptions as $memberSubscription) {
            foreach ($memberSubscription->getInvoices() as $invoice) {
                if (InvoiceStatusEnum::CREATED === $invoice->getStatusAsEnum()) {
                    $invoices[] = $invoice;
                }
            }
        }

        return $invoices;
    }
}
