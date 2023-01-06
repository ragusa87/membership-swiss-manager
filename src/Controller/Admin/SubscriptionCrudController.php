<?php

namespace App\Controller\Admin;

use App\Entity\Subscription;
use EasyCorp\Bundle\EasyAdminBundle\Config\Action;
use EasyCorp\Bundle\EasyAdminBundle\Config\Actions;
use EasyCorp\Bundle\EasyAdminBundle\Config\Crud;
use EasyCorp\Bundle\EasyAdminBundle\Context\AdminContext;
use EasyCorp\Bundle\EasyAdminBundle\Controller\AbstractCrudController;
use EasyCorp\Bundle\EasyAdminBundle\Field\IdField;
use EasyCorp\Bundle\EasyAdminBundle\Router\AdminUrlGenerator;

class SubscriptionCrudController extends AbstractCrudController
{
    private AdminUrlGenerator $adminUrlGenerator;

    public function __construct(AdminUrlGenerator $adminUrlGenerator)
    {
        $this->adminUrlGenerator = $adminUrlGenerator;
    }

    public static function getEntityFqcn(): string
    {
        return Subscription::class;
    }

    public function createEntity(string $entityFqcn)
    {
        /** @var Subscription $entity */
        $entity = parent::createEntity($entityFqcn);
        $entity->setName((int) date('Y'));

        return $entity;
    }

    public function configureCrud(Crud $crud): Crud
    {
        return $crud
            // ...
            ->showEntityActionsInlined();
    }

    public function configureActions(Actions $actions): Actions
    {
        $viewMembers = Action::new('View Members', 'View Members')
            ->linkToCrudAction('viewMembers');

        return $actions
            // ...
            // this will forbid to create or delete entities in the backend
            ->disable(Action::DELETE)
            ->add(Crud::PAGE_INDEX, $viewMembers);
    }

    public function viewMembers(AdminContext $context)
    {
        /** @var Subscription $subscription */
        $subscription = $context->getEntity()->getInstance();

        $url = $this->adminUrlGenerator
            ->setController(MemberSubscriptionCrudController::class)
            ->setAction(Action::INDEX)
            ->setEntityId(null)
            ->set('filters[subscription][value]', $subscription->getId())
            ->set('filters[subscription][comparison]', '=')
            ->generateUrl();

        return $this->redirect($url);
    }

    public function configureFields(string $pageName): iterable
    {
        return [
            IdField::new('name'),
        ];
    }
}
