<?php

namespace App\Controller\Admin;

use App\Bill\CamtProcessor;
use App\Bill\CamtSessionStorage;
use App\Bill\PdfService;
use App\Entity\Invoice;
use App\Entity\InvoiceStatusEnum;
use App\Entity\Member;
use App\Entity\MemberSubscription;
use App\Entity\Subscription;
use App\Form\CamtUploadType;
use App\Helper\InvoiceHelper;
use App\Repository\DashboardRepository;
use App\Repository\InvoiceRepository;
use App\Repository\MemberSubscriptionRepository;
use App\Repository\SubscriptionRepository;
use EasyCorp\Bundle\EasyAdminBundle\Config\Assets;
use EasyCorp\Bundle\EasyAdminBundle\Config\Dashboard;
use EasyCorp\Bundle\EasyAdminBundle\Config\MenuItem;
use EasyCorp\Bundle\EasyAdminBundle\Context\AdminContext;
use EasyCorp\Bundle\EasyAdminBundle\Controller\AbstractDashboardController;
use Genkgo\Camt\Config;
use Genkgo\Camt\Reader;
use Symfony\Component\HttpFoundation\File\UploadedFile;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\RequestStack;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Annotation\Route;
use Symfony\Component\Translation\TranslatableMessage;

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
            InvoiceHelper::class => '?'.InvoiceHelper::class,
            PdfService::class => '?'.PdfService::class,
            CamtProcessor::class => '?'.CamtProcessor::class,
            CamtSessionStorage::class => '?'.CamtSessionStorage::class,
        ]);
    }

    #[Route('/camt/process/{id}', name: 'camt_process')]
    public function camtProcess(Request $request, string $id, CamtSessionStorage $storage): Response
    {
        $object = $storage->get($id);
        if (null === $object) {
            $this->addFlash('error', 'No camt file found in session');

            return $this->redirectToRoute('admin_import_camt');
        }

        /** @var CamtProcessor $processor */
        $processor = $this->container->get(CamtProcessor::class);
        $results = $processor->parse($object)->sortByStatuses([InvoiceStatusEnum::PAID->value => 10]);

        return $this->render('camt_result.html.twig', [
            'results' => $results,
        ]);
    }

    #[Route('/admin', name: 'admin')]
    public function index(): Response
    {
        /** @var Request $request */
        $request = $this->container->get(RequestStack::class)->getCurrentRequest();
        $subscriptionName = $request?->get('routeParams') ?? [];
        $subscriptionName = $subscriptionName['subscription'] ?? null;

        $subscription = $this->getSubscriptionRepo()->getCurrentSubscription($subscriptionName);
        if (null === $subscriptionName && null !== $subscription) {
            return $this->redirectToDashboardSubscription($subscription->getName());
        }

        $memberSubscriptions = $this->getMemberSubscriptionRepository()->getActiveSubscriptions($subscription);

        return $this->render('dashboard.twig', [
            'subscription' => $subscription,
            'memberSubscriptions' => $memberSubscriptions,
            'countMembers' => $subscription ? $this->getDashboardRepo()->countMembers($subscription) : 0,
        ]);
    }

    public function configureDashboard(): Dashboard
    {
        return Dashboard::new()
            ->setTitle('App');
    }

    public function configureAssets(): Assets
    {
        return Assets::new()->addCssFile('css/environment.css');
    }

    protected function getInvoiceRepo(): InvoiceRepository
    {
        return $this->container->get(InvoiceRepository::class);
    }

    protected function getDashboardRepo(): DashboardRepository
    {
        return $this->container->get(DashboardRepository::class);
    }

    protected function getCamtStorage(): CamtSessionStorage
    {
        return $this->container->get(CamtSessionStorage::class);
    }

    public function configureMenuItems(): iterable
    {
        $countMembers = $this->getDashboardRepo()->countMembers();
        $countDueInvoices = $this->getInvoiceRepo()->countDue();

        $dashboardLink = MenuItem::subMenu('Overview', 'fa fa-home');

        $subscriptions = $this->getSubscriptionRepo()->findBy([], ['createdAt' => 'asc']);
        $subMenu = [];
        foreach ($subscriptions as $subscription) {
            $subMenu[] = MenuItem::linkToRoute($subscription->getName(), 'fa fa-book', 'admin', ['subscription' => $subscription->getName()]);
        }
        $dashboardLink->setSubItems($subMenu);

        $dashboardCamtLink = MenuItem::subMenu('Camt', 'fa fa-receipt');
        $subMenuCamt = [MenuItem::linkToRoute('import_campt', 'fa fa-upload', 'admin_import_camt')];
        foreach ($this->getCamtStorage()->getIds() as $camtIds) {
            $subMenuCamt[] = MenuItem::linkToRoute($camtIds, 'fa fa-receipt', 'camt_process', ['id' => $camtIds]);
        }
        $dashboardCamtLink->setSubItems($subMenuCamt);

        yield !empty($subMenu) ? $dashboardLink : MenuItem::linkToDashboard('Overview', 'fa fa-home');
        yield $dashboardCamtLink;
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

    #[Route('/admin/generate/{subscriptionName}', name: 'admin_generate_invoices')]
    public function generateInvoices(string $subscriptionName = null)
    {
        $subscription = $this->getSubscriptionRepo()->getCurrentSubscription($subscriptionName);
        $memberSubscriptions = $this->getMemberSubscriptionRepository()->getActiveSubscriptions($subscription);
        $invoices = $this->getInvoiceHelper()->generate($memberSubscriptions);

        $message = new TranslatableMessage('%d created invoices', ['%d' => count($invoices)]);
        $this->addFlash('success', $message);

        return $this->redirectToDashboardSubscription($subscriptionName);
    }

    #[Route('/admin/print/{subscriptionName}', name: 'admin_print_invoices')]
    public function printInvoices(string $subscriptionName = null): Response
    {
        $subscription = $this->getSubscriptionRepo()->getCurrentSubscription($subscriptionName);
        $memberSubscriptions = $this->getMemberSubscriptionRepository()->getActiveSubscriptions($subscription);
        $invoices = $this->getInvoiceHelper()->createdInvoices($memberSubscriptions);

        if (empty($invoices)) {
            $this->addFlash('warning', new TranslatableMessage('No invoices to print'));

            return $this->redirectToDashboardSubscription($subscriptionName);
        }

        return $this->getPdfService()->generate(...$invoices);
    }

    protected function getPdfService(): PdfService
    {
        return $this->container->get(PdfService::class);
    }

    protected function redirectToDashboardSubscription(string $subscriptionName): Response
    {
        return $this->redirectToRoute('admin', [
            'routeName' => 'admin',
            'routeParams' => ['subscription' => $subscriptionName],
        ]);
    }

    private function getInvoiceHelper(): InvoiceHelper
    {
        return $this->container->get(InvoiceHelper::class);
    }

    #[Route('/admin/camt/import', name: 'admin_import_camt')]
    public function importCamt(AdminContext $context, Request $request, CamtSessionStorage $storage): Response
    {
        $form = $this->createForm(CamtUploadType::class);
        $form->handleRequest($request);
        if (false === $form->isSubmitted()) {
            return $this->render('form.html.twig', [
                'form' => $form->createView(),
            ]);
        }

        if (null === $form->get('file')->getData() || false === $form->isValid()) {
            $this->addFlash('error', 'No file selected');

            return $this->render('form.html.twig', [
                'form' => $form->createView(),
            ]);
        }

        /** @var UploadedFile $file */
        $file = $form->get('file')->getData();

        $reader = new Reader(Config::getDefault());
        $message = $reader->readFile($file->getPathname());

        $id = md5_file($file->getPathname());
        unlink($file->getPathname());

        $storage->set($id, $message);

        return $this->redirectToRoute('camt_process', ['id' => $id]);
    }
}
