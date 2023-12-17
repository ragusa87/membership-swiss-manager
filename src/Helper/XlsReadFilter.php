<?php

namespace App\Helper;

use PhpOffice\PhpSpreadsheet\Reader\IReadFilter;

class XlsReadFilter implements IReadFilter
{
    /**
     * @param array<string> $columns
     */
    public function __construct(private readonly int $startRow, private readonly ?int $endRow, private readonly array $columns)
    {
    }

    public function readCell($columnAddress, $row, $worksheetName = ''): bool
    {
        if ($row >= $this->startRow && ($row <= $this->endRow || null === $this->endRow)) {
            if (in_array($columnAddress, $this->columns, true)) {
                return true;
            }
        }

        return false;
    }
}
