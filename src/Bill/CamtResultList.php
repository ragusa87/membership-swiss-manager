<?php

namespace App\Bill;

use Symfony\Component\Validator\ConstraintViolationList;

class CamtResultList
{
    public function __construct(
        private readonly ConstraintViolationList $errors,
        private readonly array $results
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
}
