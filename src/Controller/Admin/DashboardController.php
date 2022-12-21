<?php

namespace App\Controller\Admin;

use App\Entity\Invoice;
use App\Entity\Member;
use App\Entity\MemberSubscription;
use App\Entity\Subscription;
use App\Repository\DashboardRepository;
use App\Repository\InvoiceRepository;
use EasyCorp\Bundle\EasyAdminBundle\Config\Dashboard;
use EasyCorp\Bundle\EasyAdminBundle\Config\MenuItem;
use EasyCorp\Bundle\EasyAdminBundle\Controller\AbstractDashboardController;
use EasyCorp\Bundle\EasyAdminBundle\Router\AdminUrlGenerator;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Annotation\Route;

class DashboardController extends AbstractDashboardController
{
    public static function getSubscribedServices(): array
    {
        return array_merge(parent::getSubscribedServices(), [
            DashboardRepository::class => '?'.DashboardRepository::class,
            InvoiceRepository::class => '?'.InvoiceRepository::class,
        ]);
    }

    #[Route('/admin', name: 'admin')]
    public function index(): Response
    {
        // return parent::index();

        // Option 1. You can make your dashboard redirect to some common page of your backend
        //
        $adminUrlGenerator = $this->container->get(AdminUrlGenerator::class);

        $data = [
            'countMembers' => $this->getDashboardRepo()->countMembers(),
        ];

        return $this->render('dashboard.twig', $data);
//        return $this->render('@EasyAdmin/page/content.html.twig', [
//            'dashboard_controller_filepath' => (new \ReflectionClass(static::class))->getFileName(),
//        ]);
    }

    public function configureDashboard(): Dashboard
    {
        return Dashboard::new()
            ->setTitle('App');
    }

    protected function getInvoiceRepo(): InvoiceRepository
    {
        return $this->container->get(InvoiceRepository::class);
    }

    protected function getDashboardRepo(): DashboardRepository
    {
        return $this->container->get(DashboardRepository::class);
    }

    public function configureMenuItems(): iterable
    {
        $countMembers = $this->getDashboardRepo()->countMembers();
        $countDueInvoices = $this->getInvoiceRepo()->countDue();

        yield MenuItem::linkToDashboard('Dashboard', 'fa fa-home');
        yield MenuItem::linkToCrud('Subscription', 'fas fa-list', Subscription::class);
        yield MenuItem::linkToCrud('Members', 'fas fa-list', Member::class)->setBadge($countMembers);
        yield MenuItem::linkToCrud('SubscriptionMember', 'fas fa-list', MemberSubscription::class);
        yield MenuItem::linkToCrud('Invoices', 'fas fa-list', Invoice::class)->setBadge($countDueInvoices);
    }
}
