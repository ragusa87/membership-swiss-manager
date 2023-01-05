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
use EasyCorp\Bundle\EasyAdminBundle\Field\AssociationField;
use EasyCorp\Bundle\EasyAdminBundle\Field\ChoiceField;
use EasyCorp\Bundle\EasyAdminBundle\Field\IdField;
use EasyCorp\Bundle\EasyAdminBundle\Field\IntegerField;
use EasyCorp\Bundle\EasyAdminBundle\Field\MoneyField;
use EasyCorp\Bundle\EasyAdminBundle\Field\TextField;
use EasyCorp\Bundle\EasyAdminBundle\Filter\ChoiceFilter;
use EasyCorp\Bundle\EasyAdminBundle\Filter\EntityFilter;
use Symfony\Component\HttpFoundation\Response;

class InvoiceCrudController extends AbstractCrudController
{
    public static function getEntityFqcn(): string
    {
        return Invoice::class;
    }

    public function configureFilters(Filters $filters): Filters
    {
        $sub = EntityFilter::new('memberSubscription');
        // Hack so the Filter's label match memberSubscription->toLabel
        $sub->getAsDto()->setFormTypeOptionIfNotSet('value_type_options.choice_label', 'toLabel');

        return $filters
            ->add(ChoiceFilter::new('status')
                ->setChoices(InvoiceStatusEnum::choices())
            )
            ->add('price')
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
    }

    public function configureActions(Actions $actions): Actions
    {
        $exportInvoice = Action::new('Export Invoice', 'Export Invoices')
            ->linkToCrudAction('export');

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
}
