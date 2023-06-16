<?php

namespace App\Bill;

use App\Entity\Invoice;
use Genkgo\Camt\DTO\Entry;

class CamtResultItem
{
    public function __construct(
        public readonly int $amount,
        public readonly Entry $entry,
        public readonly ?string $message,
        public readonly ?string $ref,
        public readonly ?string $contact,
        public readonly ?string $transactionId,
        protected ?Invoice $invoice = null,
    ) {
    }

    public function setInvoice(Invoice $invoice = null): self
    {
        $this->invoice = $invoice;

        return $this;
    }

    public function getInvoice(): ?Invoice
    {
        return $this->invoice;
    }
}
