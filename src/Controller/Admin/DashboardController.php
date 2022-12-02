<?php

namespace App\Controller\Admin;

use App\Entity\Member;
use App\Entity\MemberSubscription;
use App\Entity\Subscription;
use App\Repository\DashboardRepository;
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
            'countMembers' => $this->container->get(DashboardRepository::class)->countMembers(),
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

    public function configureMenuItems(): iterable
    {
        yield MenuItem::linkToDashboard('Dashboard', 'fa fa-home');
        yield MenuItem::linkToCrud('Subscription', 'fas fa-list', Subscription::class);
        yield MenuItem::linkToCrud('Members', 'fas fa-list', Member::class);
        yield MenuItem::linkToCrud('SubscriptionMember', 'fas fa-list', MemberSubscription::class);
    }
}
