<?php

namespace App\Repository;

use App\Entity\Invoice;
use App\Entity\InvoiceStatusEnum;
use App\Entity\Subscription;
use Doctrine\Bundle\DoctrineBundle\Repository\ServiceEntityRepository;
use Doctrine\Persistence\ManagerRegistry;

/**
 * @extends ServiceEntityRepository<Invoice>
 *
 * @method Invoice|null find($id, $lockMode = null, $lockVersion = null)
 * @method Invoice|null findOneBy(array $criteria, array $orderBy = null)
 * @method Invoice[]    findAll()
 * @method Invoice[]    findBy(array $criteria, array $orderBy = null, $limit = null, $offset = null)
 */
class InvoiceRepository extends ServiceEntityRepository
{
    public function __construct(ManagerRegistry $registry)
    {
        parent::__construct($registry, Invoice::class);
    }

    public function save(Invoice $entity, bool $flush = false): void
    {
        $this->getEntityManager()->persist($entity);

        if ($flush) {
            $this->getEntityManager()->flush();
        }
    }

    public function remove(Invoice $entity, bool $flush = false): void
    {
        $this->getEntityManager()->remove($entity);

        if ($flush) {
            $this->getEntityManager()->flush();
        }
    }

    public function updateReferences(): void
    {
        $qb = $this->createQueryBuilder('i');
        $query = $qb->update($this->_entityName, 'i')
                  ->set('i.reference', 'i.id')
                  ->where($qb->expr()->isNull('i.reference'));

        $query->getQuery()->execute();
    }

    public function countDue(): int
    {
        $qb = $this->createQueryBuilder('i');
        $qb->where($qb->expr()->notIn('i.status', [InvoiceStatusEnum::PAID->value]));
        $query = $qb->select($qb->expr()->countDistinct('i.id'));

        return $query->getQuery()->getSingleScalarResult();
    }

    /**
     * @param array<int> $refs
     *
     * @return Invoice[]
     */
    public function findByReferences(array $refs): mixed
    {
        $qb = $this->createQueryBuilder('i');
        $qb->where($qb->expr()->in('i.reference', ':refs'));
        $qb->setParameter('refs', $refs);
        $qb->join('i.memberSubscription', 'ms');
        $qb->join('ms.member', 'm');
        $qb->select('i, ms, m');
        $qb->indexBy('i', 'i.reference');

        return $qb->getQuery()->getResult();
    }

    /**
     * @param array<string> $transactionIds
     *
     * @return Invoice[]
     */
    public function findByTransactionIds(array $transactionIds): mixed
    {
        $qb = $this->createQueryBuilder('i');
        $qb->where($qb->expr()->in('i.transactionId', ':transactionIds'));
        $qb->setParameter('transactionIds', $transactionIds);
        $qb->join('i.memberSubscription', 'ms');
        $qb->join('ms.member', 'm');
        $qb->select('i, ms, m');
        $qb->indexBy('i', 'i.transactionId');

        return $qb->getQuery()->getResult();
    }

    public function markCreatedInvoicesAsPending(Subscription $subscription): int
    {
        $qb = $this->createQueryBuilder('i');
        $qb = $qb->update();

        $qb->set('i.status', ':newStatus');
        $qb->set('i.updatedAt', ':updatedAT');
        $qb->setParameter('newStatus', InvoiceStatusEnum::PENDING->value);
        $qb->setParameter('updatedAT', new \DateTime());

        $subQuery = $this->createQueryBuilder('j');
        $subQuery->select('j.id');
        $subQuery->join('j.memberSubscription', 'ms');
        $subQuery->join('ms.subscription', 'sub');
        $subQuery->where('sub = :subscriptionParam');
        $subQuery->andWhere($qb->expr()->eq('j.status', ':oldStatus'));

        $qb->setParameter('subscriptionParam', $subscription);
        $qb->where($qb->expr()->in('i.id', $subQuery->getQuery()->getDQL()));
        $qb->setParameter('oldStatus', InvoiceStatusEnum::CREATED->value);

        return $qb->getQuery()->execute();
    }
}
