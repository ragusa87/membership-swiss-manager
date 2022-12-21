<?php

namespace App\Controller\Admin;

use App\Entity\Invoice;
use App\Entity\InvoiceStatusEnum;
use EasyCorp\Bundle\EasyAdminBundle\Config\Filters;
use EasyCorp\Bundle\EasyAdminBundle\Controller\AbstractCrudController;
use EasyCorp\Bundle\EasyAdminBundle\Field\IdField;
use EasyCorp\Bundle\EasyAdminBundle\Field\IntegerField;
use EasyCorp\Bundle\EasyAdminBundle\Field\MoneyField;
use EasyCorp\Bundle\EasyAdminBundle\Field\TextField;
use EasyCorp\Bundle\EasyAdminBundle\Filter\ChoiceFilter;
use EasyCorp\Bundle\EasyAdminBundle\Filter\EntityFilter;

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
        yield IdField::new('id');
        yield IntegerField::new('reference');
        yield TextField::new('memberSubscription.member')->setLabel('Member')->onlyOnIndex();
        yield TextField::new('memberSubscription.subscription.name')->setLabel('Subscription')->onlyOnIndex();
        yield TextField::new('status')->onlyOnIndex();
        yield MoneyField::new('price')->setStoredAsCents(true)->setCurrency('CHF');
    }
}
