<?php

namespace App\Entity;

enum InvoiceStatusEnum: string
{
    case PAID = 'paid';
    case PENDING = 'pending';
    case CREATED = 'created';

    public static function choices(): string
    {
        $choicesValues = array_map(function (self $enum) {
            return $enum->value;
        }, self::cases());
        $choicesLabels = array_map(function (self $enum) {
            return $enum->name;
        }, self::cases());

        return array_combine($choicesLabels, $choicesValues);
    }
}
