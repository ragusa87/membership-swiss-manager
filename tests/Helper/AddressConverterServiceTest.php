<?php

namespace App\Tests\Helper;

use App\Helper\AddressConverterService;
use PHPUnit\Framework\TestCase;

class AddressConverterServiceTest extends TestCase
{
    /**
     * @dataProvider provideTrimData
     */
    public function testSplit(?string $line, ?string $expectedAddress, ?string $expectedNumber): void
    {
        [$address, $number] = (new AddressConverterService())->split($line);
        $this->assertSame($expectedAddress, $address);
        $this->assertSame($expectedNumber, $number);
    }

    /**
     * @return array<array{string|null, string|null, string|null}>
     */
    public function provideTrimData(): array
    {
        return [
            [
                'Chemin du Vanil 10b',
                'Chemin du Vanil',
                '10b',
            ],
            [
                'Chemin du Vanil 10b.',
                'Chemin du Vanil',
                '10b',
            ],
            [
                'Chemin du Peuple',
                'Chemin du Peuple',
                null,
            ],
            [
                'Chemin du Peuple.',
                'Chemin du Peuple',
                null,
            ],
            [
                null,
                null,
                null,
            ],
        ];
    }
}
