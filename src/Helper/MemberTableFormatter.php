<?php

namespace App\Helper;

use App\Entity\Member;
use Symfony\Component\Console\Helper\Table;
use Symfony\Component\Console\Helper\TableCell;
use Symfony\Component\Console\Helper\TableCellStyle;
use Symfony\Component\Console\Helper\TableSeparator;

class MemberTableFormatter
{
    /**
     * @param MemberMatch[] $matches
     */
    public function fillMatches(Table $table, array $matches): Table
    {
        $table->setHeaders(['Firstname', 'Lastname', 'Email', 'Address', 'City', 'Phone', 'Parent', 'Score', 'Action']);
        foreach ($matches as $match) {
            $importedMember = $match->getMember();
            $existingMember = $match->getResult();
            $importedData = $this->userAsRow($importedMember);
            $currentData = $existingMember ? $this->userAsRow($existingMember) : array_fill(0, count($importedData), null);

            $result = [];
            foreach ($importedData as $column => $value) {
                $color = $value === $currentData[$column] ? 'default' : (null == $existingMember ? 'green' : 'red');
                $style = new TableCellStyle(['cellFormat' => '<fg='.$color.'>%s</>']);
                $result[$column] = new TableCell((string) $value, ['style' => $style]);
            }

            $matchStatus = new TableCell($match->scoreToString(), ['style' => $match->scoreTableCellStyle()]);
            $result[] = $matchStatus;
            $currentData[] = $matchStatus;
            $importedData[] = $matchStatus;

            $style = new TableCellStyle(['cellFormat' => '<fg='.(null == $existingMember ? 'green' : 'yellow').'>%s</>']);
            $action = new TableCell(null == $existingMember ? 'add' : 'edit', ['style' => $style]);
            $result[] = $action;
            $currentData[] = $action;
            $importedData[] = $action;

            // Show only one row as no previous row exists
            if (null === $existingMember) {
                $table->addRow($result);
                $table->addRow(new TableSeparator());
                continue;
            }

            $table->addRow($currentData);
            $table->addRow($result);
            $table->addRow(new TableSeparator());
        }

        return $table;
    }

    /**
     * @return array<string|null>
     */
    protected function userAsRow(Member $member): array
    {
        return [
            $member->getFirstname(),
            $member->getLastname(),
            $member->getEmail(),
            $member->getFullAddressLine1(),
            $member->getFullAddressLine2(),
            $member->getPhone(),
            $member->getParent() ? $member->getParent()->getFullname() : null,
        ];
    }
}
