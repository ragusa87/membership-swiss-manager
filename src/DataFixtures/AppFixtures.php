<?php

namespace App\DataFixtures;

use App\Entity\Invoice;
use App\Entity\InvoiceStatusEnum;
use App\Entity\Member;
use App\Entity\MemberSubscription;
use App\Entity\Subscription;
use App\Entity\SubscriptionTypeEnum;
use App\Helper\MemberXlsImporter;
use Doctrine\Bundle\FixturesBundle\Fixture;
use Doctrine\Persistence\ObjectManager;

class AppFixtures extends Fixture
{
    public function __construct(protected MemberXlsImporter $importer)
    {
    }

    public function load(ObjectManager $manager): void
    {
        $this->loadSubscriptions($manager);
        $this->loadMembers($manager);
    }

    public function loadMembers(ObjectManager $manager): void
    {
        foreach (['Gladyss', 'Laurent', 'Tom'] as $name) {
            $user = new Member();
            $user->setFirstname($name);
            $manager->persist($user);
            $this->setReference(Member::class.'_'.$name, $user);
        }
        $manager->flush();

        $memberSubscription = new MemberSubscription();
        $memberSubscription->setMember($this->getReference(Member::class.'_Gladyss'));
        $memberSubscription->setSubscription($this->getReference(Subscription::class.'_'.date('Y')));
        $memberSubscription->setTypeEnum(SubscriptionTypeEnum::MEMBER);
        $memberSubscription->setPrice($memberSubscription->getPrice());
        $this->addInvoices($manager, $memberSubscription);
        $manager->persist($memberSubscription);

        $memberSubscription = new MemberSubscription();
        $memberSubscription->setMember($this->getReference(Member::class.'_Gladyss'));
        $memberSubscription->setSubscription($this->getReference(Subscription::class.'_'.(((int) date('Y')) - 1)));
        $memberSubscription->setTypeEnum(SubscriptionTypeEnum::MEMBER);
        $memberSubscription->setPrice($memberSubscription->getPrice());
        $this->addInvoices($manager, $memberSubscription, 0.5)->setStatusFromEnum(InvoiceStatusEnum::PAID);
        $this->addInvoices($manager, $memberSubscription, 0.5);
        $manager->persist($memberSubscription);
        $manager->flush();

        $memberSubscription = new MemberSubscription();
        $memberSubscription->setMember($this->getReference(Member::class.'_Laurent'));
        $memberSubscription->setSubscription($this->getReference(Subscription::class.'_'.(((int) date('Y')) - 1)));
        $memberSubscription->setTypeEnum(SubscriptionTypeEnum::SUPPORTER);
        $memberSubscription->setPrice($memberSubscription->getPrice());
        $this->addInvoices($manager, $memberSubscription);
        $manager->persist($memberSubscription);
        $manager->flush();

        $users = $this->importer->parse(__DIR__.'/members_fixtures.xlsx');
        foreach ($users as $user) {
            $this->setReference(Member::class.'_'.$user->getFirstname(), $user);
            $manager->persist($user);
        }
        $manager->flush();
    }

    public function loadSubscriptions(ObjectManager $manager): void
    {
        $y = (int) date('Y');
        for ($i = $y - 1; $i <= $y + 1; ++$i) {
            $sub = new Subscription();
            $sub->setName((string) $i);
            $manager->persist($sub);
            $this->addReference(Subscription::class.'_'.$i, $sub);
        }
        $manager->flush();
    }

    private function addInvoices(ObjectManager $manager, MemberSubscription $memberSubscription, float $ratio = 1.0): Invoice
    {
        $invoice = new Invoice();
        $invoice->setMemberSubscription($memberSubscription);
        $invoice->setPrice((int) ($memberSubscription->getPrice() * $ratio));
        $manager->persist($invoice);

        return $invoice;
    }
}
