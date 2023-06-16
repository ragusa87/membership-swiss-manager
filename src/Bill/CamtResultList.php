<?php

namespace App\Bill;

use Symfony\Component\Validator\ConstraintViolationList;

class CamtResultList
{
    public function __construct(
        private readonly ConstraintViolationList $errors,
        private array $results
    ) {
    }

    public function getErrors(): ConstraintViolationList
    {
        return $this->errors;
    }

    /** @return CamtResultItem[] */
    public function getResults(): array
    {
        return $this->results;
    }

    public function sortByStatuses(array $statusMap = []): self
    {
        uasort($this->results, function (CamtResultItem $a, CamtResultItem $b) use ($statusMap) {
            return ($statusMap[$a->getInvoice()->getStatus() ?? null] ?? 0) <=> ($statusMap[$b->getInvoice()->getStatus() ?? null] ?? 0);
        });

        return $this;
    }
}
