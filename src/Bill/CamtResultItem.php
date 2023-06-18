<?php

namespace App\Bill;

use App\Entity\Invoice;
use Genkgo\Camt\DTO\Entry;
use Genkgo\Camt\DTO\EntryTransactionDetail;
use kmukku\phpIso11649\phpIso11649;

class CamtResultItem
{
    public function __construct(
        public readonly int $amount,
        public readonly Entry $entry,
        public readonly EntryTransactionDetail $transactionDetail,
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

    public function getReferenceString(): ?string
    {
        return $this->ref;
    }

    public function getReferenceInt(): ?int
    {
        $iso = new phpIso11649();

        if (false === $iso->validateRfReference($this->ref)) {
            return null;
        }
        $refId = (int) substr($this->ref, 4);

        return $refId > 0 ? $refId : null;
    }
}
