<?php

namespace App\Entity;

enum SubscriptionTypeEnum: string
{
    case MEMBER = 'member';
    case SUPPORTER = 'supporter';

    public static function choices(): array
    {
        $choicesValues = array_map(function (SubscriptionTypeEnum $enum) {
            return $enum->value;
        }, self::cases());
        $choicesLabels = array_map(function (SubscriptionTypeEnum $enum) {
            return $enum->name;
        }, self::cases());

        return array_combine($choicesLabels, $choicesValues);
    }
}
