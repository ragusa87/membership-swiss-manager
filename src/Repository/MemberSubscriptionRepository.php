<?php

namespace App\Repository;

use App\Entity\Member;
use App\Entity\MemberSubscription;
use App\Entity\Subscription;
use Doctrine\Bundle\DoctrineBundle\Repository\ServiceEntityRepository;
use Doctrine\Persistence\ManagerRegistry;

/**
 * @extends ServiceEntityRepository<MemberSubscription>
 *
 * @method MemberSubscription|null find($id, $lockMode = null, $lockVersion = null)
 * @method MemberSubscription|null findOneBy(array $criteria, array $orderBy = null)
 * @method MemberSubscription[]    findAll()
 * @method MemberSubscription[]    findBy(array $criteria, array $orderBy = null, $limit = null, $offset = null)
 */
class MemberSubscriptionRepository extends ServiceEntityRepository
{
    public function __construct(ManagerRegistry $registry)
    {
        parent::__construct($registry, MemberSubscription::class);
    }

    public function save(MemberSubscription $entity, bool $flush = false): void
    {
        $this->getEntityManager()->persist($entity);

        if ($flush) {
            $this->getEntityManager()->flush();
        }
    }

    public function remove(MemberSubscription $entity, bool $flush = false): void
    {
        $this->getEntityManager()->remove($entity);

        if ($flush) {
            $this->getEntityManager()->flush();
        }
    }

    /**
     * @param array<int>|array<Member> $usersIds
     */
    public function subscribe(Subscription $subscription, array $usersIds): void
    {
        // Keep only parents, not children
        $usersIds = array_filter($usersIds, fn (Member $member) => null === $member->getParent());

        /** @var MemberRepository $memberRepository */
        $memberRepository = $this->getEntityManager()->getRepository(Member::class);
        $membersWithId = array_filter($usersIds, fn (Member $member) => null !== $member->getId());
        $memberWithoutId = array_filter($usersIds, fn (Member $member) => null == $member->getId());
        $members = $memberRepository->findByIdWithSubscription($membersWithId);
        foreach ($memberWithoutId as $member) {
            $members[] = $member;
        }

        foreach ($members as $user) {
            if (null !== $user->getMemberSubscriptionBySubscription($subscription)) {
                continue;
            }
            $ms = new MemberSubscription();
            $ms->setMember($user);
            $ms->setSubscription($subscription);
            $this->getEntityManager()->persist($ms);

            $user->addMemberSubscription($ms);
        }
    }

    public function getActiveSubscriptions(?Subscription $subscription): mixed
    {
        if (null === $subscription) {
            return [];
        }
        $qb = $this->createQueryBuilder('memberSubscription')
            ->where('memberSubscription.subscription = :subscription')
            ->andWhere('memberSubscription.active = :active')
            ->setParameter('subscription', $subscription)
            ->setParameter('active', true)
            ->leftJoin('memberSubscription.member', 'm')
            ->leftJoin('memberSubscription.subscription', 's')
            ->leftJoin('memberSubscription.invoices', 'i')
            ->leftJoin('m.children', 'c')
            ->addSelect('m')
            ->addSelect('s')
            ->addSelect('i')
            ->addSelect('c')
            ->orderBy('memberSubscription.type', 'asc');

        return $qb->getQuery()->getResult();
    }
}
