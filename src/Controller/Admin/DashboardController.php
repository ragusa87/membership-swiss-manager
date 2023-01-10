<?php

namespace App\Controller\Admin;

use App\Entity\Invoice;
use App\Entity\Member;
use App\Entity\MemberSubscription;
use App\Entity\Subscription;
use App\Repository\DashboardRepository;
use App\Repository\InvoiceRepository;
use App\Repository\MemberSubscriptionRepository;
use App\Repository\SubscriptionRepository;
use EasyCorp\Bundle\EasyAdminBundle\Config\Dashboard;
use EasyCorp\Bundle\EasyAdminBundle\Config\MenuItem;
use EasyCorp\Bundle\EasyAdminBundle\Controller\AbstractDashboardController;
use Symfony\Component\HttpFoundation\RequestStack;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Annotation\Route;

class DashboardController extends AbstractDashboardController
{
    public static function getSubscribedServices(): array
    {
        return array_merge(parent::getSubscribedServices(), [
            SubscriptionRepository::class => '?'.SubscriptionRepository::class,
            DashboardRepository::class => '?'.DashboardRepository::class,
            InvoiceRepository::class => '?'.InvoiceRepository::class,
            MemberSubscriptionRepository::class => '?'.MemberSubscriptionRepository::class,
            RequestStack::class => '?'.RequestStack::class,
        ]);
    }

    #[Route('/admin', name: 'admin')]
    public function index(): Response
    {
        $subscriptionName = $this->container->get(RequestStack::class)->getCurrentRequest()->query->get('subscription') ?? null;
        $subscription = $this->getSubscriptionRepo()->getCurrentSubscription($subscriptionName);
        $memberSubscriptions = $this->getMemberSubscriptionRepository()->getActiveSubscriptions($subscription);

        return $this->render('dashboard.twig', [
                'subscription' => $subscription,
                'memberSubscriptions' => $memberSubscriptions,
                'countMembers' => $this->getDashboardRepo()->countMembers(),
       ]);
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

    private function getSubscriptionRepo(): SubscriptionRepository
    {
        return $this->container->get(SubscriptionRepository::class);
    }

    private function getMemberSubscriptionRepository(): MemberSubscriptionRepository
    {
        return $this->container->get(MemberSubscriptionRepository::class);
    }
}
