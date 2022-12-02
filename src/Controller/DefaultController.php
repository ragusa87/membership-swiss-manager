<?php

namespace App\Controller;

use App\Controller\Admin\DashboardController;
use EasyCorp\Bundle\EasyAdminBundle\Config\Action;
use EasyCorp\Bundle\EasyAdminBundle\Router\AdminUrlGenerator;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\Routing\Annotation\Route;

class DefaultController extends AbstractController
{
    #[Route('/')]
    public function index(AdminUrlGenerator $adminUrlGenerator)
    {
        return $this->redirect($adminUrlGenerator
            ->setController(DashboardController::class)
            ->setAction(Action::INDEX)
            ->generateUrl());
    }
}
