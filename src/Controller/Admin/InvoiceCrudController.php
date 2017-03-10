<?php

namespace App\Controller\Admin;

use App\Bill\PdfService;
use App\Entity\Invoice;
use App\Entity\InvoiceStatusEnum;
use App\Entity\MemberSubscription;
use EasyCorp\Bundle\EasyAdminBundle\Config\Action;
use EasyCorp\Bundle\EasyAdminBundle\Config\Actions;
use EasyCorp\Bundle\EasyAdminBundle\Config\Crud;
use EasyCorp\Bundle\EasyAdminBundle\Config\Filters;
use EasyCorp\Bundle\EasyAdminBundle\Context\AdminContext;
use EasyCorp\Bundle\EasyAdminBundle\Controller\AbstractCrudController;
use EasyCorp\Bundle\EasyAdminBundle\Dto\BatchActionDto;
use EasyCorp\Bundle\EasyAdminBundle\Field\AssociationField;
use EasyCorp\Bundle\EasyAdminBundle\Field\ChoiceField;
use EasyCorp\Bundle\EasyAdminBundle\Field\DateField;
use EasyCorp\Bundle\EasyAdminBundle\Field\IdField;
use EasyCorp\Bundle\EasyAdminBundle\Field\IntegerField;
use EasyCorp\Bundle\EasyAdminBundle\Field\MoneyField;
use EasyCorp\Bundle\EasyAdminBundle\Field\TextField;
use EasyCorp\Bundle\EasyAdminBundle\Filter\ChoiceFilter;
use EasyCorp\Bundle\EasyAdminBundle\Filter\EntityFilter;
use EasyCorp\Bundle\EasyAdminBundle\Filter\NumericFilter;
use Symfony\Component\HttpFoundation\Response;

class InvoiceCrudController extends AbstractCrudController
{
    final public const ACTION_UPLOAD_CAMT = 'uploadCamt';

    public static function getEntityFqcn(): string
    {
        return Invoice::class;
    }

    public function configureCrud(Crud $crud): Crud
    {
        return $crud
            ->showEntityActionsInlined()
        ;
    }

    public function configureFilters(Filters $filters): Filters
    {
        $sub = EntityFilter::new('memberSubscription');
        // Hack so the Filter's label match memberSubscription->toLabel
        $sub->getAsDto()->setFormTypeOptionIfNotSet('value_type_options.choice_label', 'toLabel');

        return $filters
            ->add(NumericFilter::new('id'))
            ->add(NumericFilter::new('reference'))
            ->add(ChoiceFilter::new('status')
                ->setChoices(InvoiceStatusEnum::choices())
            )
            ->add('price')
            ->add('reminder')
            ->add($sub);
        // ->add(EntityFilter::new('memberSubscription.member'));
    }

    public function configureFields(string $pageName): iterable
    {
        yield IdField::new('id')->setRequired(false)->hideWhenCreating();
        yield IntegerField::new('reference')->hideWhenCreating();
        yield TextField::new('memberSubscription.member')->setLabel('Member')->onlyOnIndex();
        yield TextField::new('memberSubscription.subscription.name')->setLabel('Subscription')->onlyOnIndex();
        $sub = AssociationField::new('memberSubscription')->setLabel('memberSubscription');
        $sub->getAsDto()->setFormTypeOptionIfNotSet('choice_label', 'toLabel');
        yield $sub->onlyOnForms();
        yield TextField::new('status')->onlyOnIndex();
        yield ChoiceField::new('status')->setChoices(InvoiceStatusEnum::choices())->onlyOnForms()->setEmptyData(InvoiceStatusEnum::CREATED->value)->hideWhenCreating();
        yield MoneyField::new('price')->setStoredAsCents(true)->setCurrency('CHF');
        yield DateField::new('created_at')->onlyOnIndex();
        yield DateField::new('updated_at')->onlyOnIndex();
        yield IntegerField::new('reminder')->hideWhenCreating();
        yield TextField::new('transactionId')->hideWhenCreating();
    }

    public function configureActions(Actions $actions): Actions
    {
        $exportInvoice = Action::new('Export Invoice', 'Export Invoice')
            ->linkToCrudAction('export');

        $actions->addBatchAction(Action::new('Export Invoices', 'Export Invoices')
        ->linkToCrudAction('exportBatch')
        ->addCssClass('btn btn-primary'));

        $actions->add(Crud::PAGE_INDEX, $exportInvoice);

        return $actions;
    }

    public function export(AdminContext $context): Response
    {
        /** @var Invoice $invoice */
        $invoice = $context->getEntity()->getInstance();
        /** @var PdfService $pdfService */
        $pdfService = $this->container->get(PdfService::class);

        return $pdfService->generate($invoice);
    }

    public static function getSubscribedServices(): array
    {
        return array_merge(parent::getSubscribedServices(), [
            PdfService::class,
        ]);
    }

    public function exportBatch(BatchActionDto $batchActionDto): Response
    {
        $className = $batchActionDto->getEntityFqcn();
        $entityManager = $this->container->get('doctrine')->getManagerForClass($className);
        $invoices = [];
        foreach ($batchActionDto->getEntityIds() as $id) {
            $invoices[] = $entityManager->find($className, $id);
        }
        array_filter($invoices);
        /** @var PdfService $pdfService */
        $pdfService = $this->container->get(PdfService::class);

        return $pdfService->generate(...$invoices);
    }
}
