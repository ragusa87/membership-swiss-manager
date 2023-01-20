<?php

namespace App\Repository;

use App\Entity\Member;
use App\Entity\Subscription;
use Doctrine\ORM\EntityManager;
use Doctrine\ORM\Query\Parser;
use Doctrine\ORM\Query\ResultSetMapping;
use Doctrine\Persistence\ManagerRegistry;

class DashboardRepository
{
    private ManagerRegistry $registry;

    public function __construct(ManagerRegistry $registry)
    {
        $this->registry = $registry;
    }

    /**
     * We count each member and children for the given subscription.
     * Count all user on empty subscription.
     */
    public function countMembers(?Subscription $subscription = null): int
    {
        /** @var EntityManager $manager */
        $manager = $this->registry->getManagerForClass(Member::class);

        /** @var MemberRepository $memberRepository */
        $memberRepository = $manager->getRepository(Member::class);

        if (null === $subscription) {
            return $memberRepository->count([]);
        }

        // Create the list of member_count and nb_children per user.
        $qb = $memberRepository->createQueryBuilder('m');
        $qb->select('count(m.id) as member_count')
            ->groupBy('m.id')
        ->addSelect('count(children.id) as nb_children')
            ->leftJoin('m.children', 'children')
            ->join('m.memberSubscription', 'ms')
            ->join('ms.subscription', 'sub')
            ->where('sub = '.(int) $subscription->getId()); // we avoid using a parameter to simplify the query

        // Parse query to get the resultSet mapping for nb_children and member_count (they look like sclr_0 and sclr_1)
        $parser = new Parser($qb->getQuery());
        $parser->parse();
        $mapping = array_flip($parser->getParserResult()->getResultSetMapping()->scalarMappings);

        // Sum the number of nb_children + count the number of member in a scalar query using a native query
        $sqlSelect = sprintf('SELECT SUM(sub.%s) + count(sub.%s) as nb', $mapping['nb_children'], $mapping['member_count']);
        $subQuery = $sqlSelect.sprintf(' FROM (%s) AS sub', $qb->getQuery()->getSQL());

        $rsm = new ResultSetMapping();
        $rsm->addScalarResult('nb', 'nb');

        return $manager->createNativeQuery($subQuery, $rsm)->getSingleScalarResult();
    }
}
