<?php

namespace App\Bill;

use Symfony\Component\Validator\ConstraintViolationList;

class CamtResultList
{
    public function __construct(
        private readonly ConstraintViolationList $errors,
        /** @var CamtResultItem[] $results */
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

    /**
     * @param array<string, int> $statusMap
     *
     * @return $this
     */
    public function sortByStatuses(array $statusMap = []): self
    {
        uasort($this->results, function (CamtResultItem $a, CamtResultItem $b) use ($statusMap) {
            return ($statusMap[$a->getInvoice()?->getStatus()] ?? 0) <=> ($statusMap[$b->getInvoice()?->getStatus()] ?? 0);
        });

        return $this;
    }
}
