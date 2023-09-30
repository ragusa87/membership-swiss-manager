<?php

namespace App\EventSubscriber;

use App\Entity\Invoice;
use App\Repository\InvoiceRepository;
use Doctrine\Bundle\DoctrineBundle\Attribute\AsDoctrineListener;
use Doctrine\Common\EventSubscriber;
use Doctrine\ORM\Event\PreFlushEventArgs as PreFlushEventArgsAlias;
use Doctrine\ORM\Events;

#[AsDoctrineListener('postFlush')]
#[AsDoctrineListener('preFlush')]
class InvoiceReferenceSubscriber implements EventSubscriber
{
    private bool $mustRun = false;

    public function postFlush(\Doctrine\ORM\Event\PostFlushEventArgs $args): void
    {
        if (!$this->mustRun) {
            return;
        }
        /** @var InvoiceRepository $repo */
        $repo = $args->getObjectManager()->getRepository(Invoice::class);
        $repo->updateReferences();
        $this->mustRun = false;
    }

    public function preFlush(PreFlushEventArgsAlias $args): void
    {
        $uow = $args->getObjectManager()->getUnitOfWork();
        foreach ($uow->getScheduledEntityInsertions() as $ei) {
            if ($ei instanceof Invoice) {
                $this->mustRun = true;
            }
        }
    }

    public function getSubscribedEvents(): array
    {
        return [
            Events::preFlush,
            Events::postFlush,
        ];
    }
}
