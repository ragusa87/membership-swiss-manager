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
use EasyCorp\Bundle\EasyAdminBundle\Field\BooleanField;
use EasyCorp\Bundle\EasyAdminBundle\Field\ChoiceField;
use EasyCorp\Bundle\EasyAdminBundle\Field\MoneyField;
use EasyCorp\Bundle\EasyAdminBundle\Field\TextField;
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

        yield ChoiceField::new('type')->setChoices(SubscriptionTypeEnum::choices());

        yield MoneyField::new('price')
            ->setNumDecimals(2)
            ->setStoredAsCents(true)
            ->setCurrency('CHF');

        yield MoneyField::new('dueAmount')
            ->setNumDecimals(2)
            ->setStoredAsCents(true)
            ->setCurrency('CHF')
            ->onlyOnIndex();

        yield BooleanField::new('active')->setDisabled(Crud::PAGE_INDEX === $pageName);

        yield TextField::new('comment')->hideOnIndex();
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
            ->add('id')
            ->add('active');
    }

    public function createEntity(string $entityFqcn): MemberSubscription
    {
        /** @var MemberSubscription $e */
        $e = new $entityFqcn();
        $e->setPrice(MemberSubscription::getPriceByType($e->getTypeEnum()));

        return $e;
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
            ->unset('filters')
            ->set('filters[memberSubscription][value]', $memberSubscription->getId())
            ->set('filters[memberSubscription][comparison]', '=')
            ->generateUrl();

        return $this->redirect($url);
    }
}
