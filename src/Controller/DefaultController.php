<?php

namespace App\Controller;

use App\Controller\Admin\DashboardController;
use App\Controller\Admin\InvoiceCrudController;
use App\Entity\InvoiceStatusEnum;
use App\Repository\InvoiceRepository;
use Doctrine\ORM\EntityManagerInterface;
use EasyCorp\Bundle\EasyAdminBundle\Config\Action;
use EasyCorp\Bundle\EasyAdminBundle\Router\AdminUrlGenerator;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\Routing\Annotation\Route;

class DefaultController extends AbstractController
{
    #[Route('/')]
    public function index(AdminUrlGenerator $adminUrlGenerator)
    {
        return $this->redirect($adminUrlGenerator
            ->setController(DashboardController::class)
            ->setAction(Action::INDEX)
            ->generateUrl());
    }

    #[Route(path: '/subscription-id/{id}', name: 'view_invoice_by_subscription_id')]
    public function getInvoicesBySubscriptionId(int $id, AdminUrlGenerator $generator)
    {
        $url = $generator->setController(InvoiceCrudController::class)
            ->set('filters[memberSubscription][comparison]', '=')
            ->set('filters[memberSubscription][value]', $id)
            ->generateUrl();

        return $this->redirect($url);
    }

    #[Route(path: '/invoice-id/{id}', name: 'view_invoice_by_id')]
    public function getInvoicesById(int $id, AdminUrlGenerator $generator)
    {
        $url = $generator->setController(InvoiceCrudController::class)
            ->set('filters[id][comparison]', '=')
            ->set('filters[id][value]', $id)
            ->generateUrl();

        return $this->redirect($url);
    }

    #[Route(path: '/pay-invoice-id/{id}', name: 'pay_invoice_by_id')]
    public function payInvoicesById(int $id, Request $request, EntityManagerInterface $em, InvoiceRepository $invoiceRepository)
    {
        $invoice = $invoiceRepository->find($id);
        if (null === $invoice) {
            throw $this->createNotFoundException('Invoice not found');
        }
        if (InvoiceStatusEnum::PAID === $invoice->getStatusAsEnum()) {
            throw $this->createAccessDeniedException('Invoice already paid');
        }

        $status = $request->query->get('status');
        if (false === in_array($status, [null, 'paid'], true)) {
            throw $this->createAccessDeniedException('Unsupported status '.$status);
        }

        $invoice->setStatusFromEnum(InvoiceStatusEnum::PAID);

        $price = $request->query->getInt('amount');

        if (0 !== $price) {
            $invoice->setPrice($price);
        }

        $invoice->setUpdatedAt(new \DateTime());
        $em->persist($invoice);
        $em->flush();

        return $this->redirect($request->headers->get('referer') ?? $this->generateUrl('index'));
    }
}
