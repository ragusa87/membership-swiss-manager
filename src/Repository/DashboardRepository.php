<?php

namespace App\Repository;

use App\Entity\Member;
use Doctrine\Persistence\ManagerRegistry;

class DashboardRepository
{
    private ManagerRegistry $registry;

    public function __construct(ManagerRegistry $registry)
    {
        $this->registry = $registry;
    }

    public function countMembers(): int
    {
        return $this->registry->getManagerForClass(Member::class)->getRepository(Member::class)->count([]);
    }
}
