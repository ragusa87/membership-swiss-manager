<?php

namespace App\Controller\Admin;

use App\Entity\MemberSubscription;
use App\Entity\SubscriptionTypeEnum;
use EasyCorp\Bundle\EasyAdminBundle\Config\Action;
use EasyCorp\Bundle\EasyAdminBundle\Config\Actions;
use EasyCorp\Bundle\EasyAdminBundle\Config\Crud;
use EasyCorp\Bundle\EasyAdminBundle\Config\Filters;
use EasyCorp\Bundle\EasyAdminBundle\Context\AdminContext;
use EasyCorp\Bundle\EasyAdminBundle\Controller\AbstractCrudController;
use EasyCorp\Bundle\EasyAdminBundle\Field\AssociationField;
use EasyCorp\Bundle\EasyAdminBundle\Field\MoneyField;
use EasyCorp\Bundle\EasyAdminBundle\Filter\ChoiceFilter;

class MemberSubscriptionCrudController extends AbstractCrudController
{
    public static function getEntityFqcn(): string
    {
        return MemberSubscription::class;
    }

    public function configureFields(string $pageName): iterable
    {
        if (!str_contains($pageName, '-from-member')) {
            yield AssociationField::new('member');
        }
        if (!str_contains($pageName, 'edit-from-member')) {
            yield AssociationField::new('subscription');
        } else {
            yield AssociationField::new('subscription')->setDisabled();
        }

        yield MoneyField::new('price')
            ->setNumDecimals(2)
            ->setStoredAsCents(true)
            ->setCurrency('CHF');
    }

    public function configureCrud(Crud $crud): Crud
    {
        return $crud
            // ...
            ->showEntityActionsInlined();
    }

    public function configureFilters(Filters $filters): Filters
    {
        return $filters
            ->add(ChoiceFilter::new('type')
                ->setChoices(SubscriptionTypeEnum::choices())
            )
            ->add('member')
            ->add('subscription');
    }

    public function configureActions(Actions $actions): Actions
    {
        $viewInvoice = Action::new('View Invoice', 'View Invoices')
            ->displayIf(static function (MemberSubscription $entity) {
                return $entity->getPrice() > 0;
            })
            ->linkToCrudAction('renderInvoice');

        $actions->add(Crud::PAGE_INDEX, $viewInvoice);

        return $actions;
    }

    public function renderInvoice(AdminContext $context)
    {
        /** @var MemberSubscription $memberSubscription */
        $memberSubscription = $context->getEntity()->getInstance();
        foreach ($memberSubscription->getInvoice() as $invoice) {
            dump($invoice->getId());
        }
        exit;
    }
}
