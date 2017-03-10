<?php

namespace App\Controller\Admin;

use App\Entity\Member;
use EasyCorp\Bundle\EasyAdminBundle\Config\Filters;
use EasyCorp\Bundle\EasyAdminBundle\Controller\AbstractCrudController;
use EasyCorp\Bundle\EasyAdminBundle\Field\AssociationField;
use EasyCorp\Bundle\EasyAdminBundle\Field\CollectionField;
use EasyCorp\Bundle\EasyAdminBundle\Field\EmailField;
use EasyCorp\Bundle\EasyAdminBundle\Field\IntegerField;
use EasyCorp\Bundle\EasyAdminBundle\Field\TextEditorField;
use EasyCorp\Bundle\EasyAdminBundle\Field\TextField;

class MemberCrudController extends AbstractCrudController
{
    public static function getEntityFqcn(): string
    {
        return Member::class;
    }

    public function configureFilters(Filters $filters): Filters
    {
        return $filters
            ->add('id')
            ->add('email')
            ->add('lastname')
            ->add('firstname')
            ->add('memberSubscription');
    }

    public function configureFields(string $pageName): iterable
    {
        yield TextField::new('firstname')->setFormTypeOption('attr', ['placeholder' => 'William']);
        yield TextField::new('lastname')->setFormTypeOption('attr', ['placeholder' => 'Shakespeare']);
        yield EmailField::new('email')->setFormTypeOption('attr', ['placeholder' => 'email@example.com']);
        yield TextEditorField::new('comment');

        yield AssociationField::new('parent')
            ->setRequired(false);

        if (in_array($pageName, ['new', 'edit'])) {
            yield TextField::new('address')->setRequired(false)->setFormTypeOption('attr', ['placeholder' => 'Chemin du Vanil']);
            yield TextField::new('address_number')->setRequired(false)->setFormTypeOption('attr', ['placeholder' => '10']);
            yield TextField::new('city')->setRequired(false)->setFormTypeOption('attr', ['placeholder' => 'Lausanne']);
            yield IntegerField::new('zip')->setRequired(false)->setFormTypeOption('attr', ['placeholder' => '1006']);
            yield TextField::new('phone')->setRequired(false)->setFormTypeOption('attr', ['placeholder' => '+41 7x xxx xx xx']);
        }

        if ('edit' !== $pageName && 'index' !== $pageName) {
            yield CollectionField::new('memberSubscription')
                ->setLabel('memberSubscription')
                ->useEntryCrudForm(null, $pageName.'-new-from-member', $pageName.'-edit-from-member')
                ->setEntryIsComplex(true)
                ->renderExpanded(true)
                ->allowAdd()
                ->setRequired(false);
        }
    }
}
