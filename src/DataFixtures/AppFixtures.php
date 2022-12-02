<?php

namespace App\DataFixtures;

use App\Entity\Member;
use App\Entity\MemberSubscription;
use App\Entity\Subscription;
use App\Entity\SubscriptionTypeEnum;
use Doctrine\Bundle\FixturesBundle\Fixture;
use Doctrine\Persistence\ObjectManager;

class AppFixtures extends Fixture
{
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
        $manager->persist($memberSubscription);

        $memberSubscription = new MemberSubscription();
        $memberSubscription->setMember($this->getReference(Member::class.'_Gladyss'));
        $memberSubscription->setSubscription($this->getReference(Subscription::class.'_'.(((int) date('Y')) - 1)));
        $memberSubscription->setTypeEnum(SubscriptionTypeEnum::MEMBER);
        $manager->persist($memberSubscription);
        $manager->flush();
    }

    public function loadSubscriptions(ObjectManager $manager): void
    {
        $y = (int) date('Y');
        for ($i = $y - 1; $i <= $y + 1; ++$i) {
            $sub = new Subscription();
            $sub->setName($i);
            $manager->persist($sub);
            $this->addReference(Subscription::class.'_'.$i, $sub);
        }
        $manager->flush();
    }
}
