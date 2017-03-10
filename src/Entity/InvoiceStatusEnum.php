<?php

namespace App\Entity;

enum InvoiceStatusEnum: string
{
    case PAID = 'paid';
    case PENDING = 'pending';
    case CREATED = 'created';

    case CANCELED = 'canceled';

    /**
     * @return array<string,string>
     */
    public static function choices(): array
    {
        $choicesValues = array_map(fn (self $enum) => $enum->value, self::cases());
        $choicesLabels = array_map(fn (self $enum) => $enum->name, self::cases());

        return array_combine($choicesLabels, $choicesValues);
    }
}
