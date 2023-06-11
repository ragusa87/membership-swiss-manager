<?php

namespace App\Repository;

use App\Entity\Invoice;
use App\Entity\InvoiceStatusEnum;
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

    public function updateReferences()
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

    public function findByReferences(array $refs)
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
}
