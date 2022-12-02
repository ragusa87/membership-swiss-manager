<?php

namespace App\Controller\Admin;

use App\Entity\Member;
use EasyCorp\Bundle\EasyAdminBundle\Controller\AbstractCrudController;
use EasyCorp\Bundle\EasyAdminBundle\Field\CollectionField;
use EasyCorp\Bundle\EasyAdminBundle\Field\EmailField;
use EasyCorp\Bundle\EasyAdminBundle\Field\TextEditorField;
use EasyCorp\Bundle\EasyAdminBundle\Field\TextField;

class MemberCrudController extends AbstractCrudController
{
    public static function getEntityFqcn(): string
    {
        return Member::class;
    }

    public function configureFields(string $pageName): iterable
    {
        yield TextField::new('firstname')->setLabel("firstname from $pageName");
        yield TextField::new('lastname');
        yield EmailField::new('email');
        yield TextEditorField::new('comment');

        if ('edit' !== $pageName) {
            yield CollectionField::new('memberSubscription')
                ->setLabel('memberSubscription while on page '.$pageName)
                ->useEntryCrudForm(null, $pageName.'-new-from-member', $pageName.'-edit-from-member')
                ->setEntryIsComplex(true)
                ->renderExpanded(true)
                ->allowAdd()
                ->setRequired(false);
        }
    }
}
