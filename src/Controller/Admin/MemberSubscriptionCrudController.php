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
use EasyCorp\Bundle\EasyAdminBundle\Router\AdminUrlGenerator;
use Symfony\Component\HttpFoundation\Response;

class MemberSubscriptionCrudController extends AbstractCrudController
{
    private AdminUrlGenerator $adminUrlGenerator;

    public function __construct(AdminUrlGenerator $adminUrlGenerator)
    {
        $this->adminUrlGenerator = $adminUrlGenerator;
    }

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

        yield MoneyField::new('dueAmount')
            ->setNumDecimals(2)
            ->setStoredAsCents(true)
            ->setCurrency('CHF')
            ->onlyOnIndex();
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
            ->add('subscription')
            ->add('id');
    }

    public function configureActions(Actions $actions): Actions
    {
        $viewInvoice = Action::new('View Invoice', 'View Invoices')
            ->displayIf(static function (MemberSubscription $entity) {
                return $entity->getPrice() > 0;
            })
            ->linkToCrudAction('viewInvoices');

        $actions->add(Crud::PAGE_INDEX, $viewInvoice);

        return $actions;
    }

    public function viewInvoices(AdminContext $context): Response
    {
        /** @var MemberSubscription $memberSubscription */
        $memberSubscription = $context->getEntity()->getInstance();

        $url = $this->adminUrlGenerator
            ->setController(InvoiceCrudController::class)
            ->setAction(Action::INDEX)
            ->setEntityId(null)
            ->set('filters[memberSubscription][value]', $memberSubscription->getId())
            ->set('filters[memberSubscription][comparison]', '=')
            ->generateUrl();

        return $this->redirect($url);
    }
}
