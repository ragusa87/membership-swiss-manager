<?php

namespace App\Helper;

use PhpOffice\PhpSpreadsheet\Reader\IReadFilter;

class XlsReadFilter implements IReadFilter
{
    private int $startRow = 0;

    private ?int $endRow = null;

    private array $columns = [];

    public function __construct(int $startRow, ?int $endRow, array $columns)
    {
        $this->startRow = $startRow;
        $this->endRow = $endRow;
        $this->columns = $columns;
    }

    public function readCell($columnAddress, $row, $worksheetName = '')
    {
        if ($row >= $this->startRow && ($row <= $this->endRow || null === $this->endRow)) {
            if (in_array($columnAddress, $this->columns)) {
                return true;
            }
        }

        return false;
    }
}
