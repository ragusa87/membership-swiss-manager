<?php

namespace App\Helper;

class AddressConverterService
{
    /**
     * @return array{0: string|null, 1: string|null}
     */
    public function split(?string $address): array
    {
        $matches = [];
        if (null !== $address && false !== preg_match('/^(.+)\s(\S+)$/', $address, $matches)) {
            $number = rtrim($matches[2], '.');
            // Skip address without numbers
            if (0 === preg_match('/^[0-9abcABC\.]+$/', $number)) {
                return [rtrim($address, '.'), null];
            }

            return [trim($matches[1]), trim(rtrim($matches[2], '.'))];
        }

        return [$address, null];
    }
}
