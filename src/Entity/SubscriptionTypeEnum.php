<?php

namespace App\Entity;

enum SubscriptionTypeEnum: string
{
    case MEMBER = 'member';
    case SUPPORTER = 'supporter';

    /**
     * @return array<string,string>
     */
    public static function choices(): array
    {
        $choicesValues = array_map(fn (SubscriptionTypeEnum $enum) => $enum->value, self::cases());
        $choicesLabels = array_map(fn (SubscriptionTypeEnum $enum) => sprintf('subscription_type_enum.%s', $enum->value), self::cases());

        return array_combine($choicesLabels, $choicesValues);
    }
}
