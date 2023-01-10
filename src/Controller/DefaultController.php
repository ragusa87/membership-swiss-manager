<?php

namespace App\Controller;

use App\Controller\Admin\DashboardController;
use App\Controller\Admin\InvoiceCrudController;
use EasyCorp\Bundle\EasyAdminBundle\Config\Action;
use EasyCorp\Bundle\EasyAdminBundle\Router\AdminUrlGenerator;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
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
}
