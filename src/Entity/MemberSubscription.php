<?php

namespace App\Entity;

use App\Repository\MemberSubscriptionRepository;
use Doctrine\ORM\Mapping as ORM;
use Symfony\Bridge\Doctrine\Validator\Constraints\UniqueEntity;
use Gedmo\Timestampable\Traits\TimestampableEntity;
#[ORM\Entity(repositoryClass: MemberSubscriptionRepository::class)]
#[UniqueEntity(
    fields: ['subscription', 'member'],
    errorPath: 'subscription',
    message: 'This user is already subscribed to this subscription.',
)]
class MemberSubscription
{
    use TimestampableEntity;

    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    private ?int $id = null;

    #[ORM\Column(length: 255)]
    private string $type;

    #[ORM\ManyToOne(inversedBy: 'subscription')]
    #[ORM\JoinColumn(nullable: false)]
    private ?Subscription $subscription = null;

    #[ORM\ManyToOne(inversedBy: 'memberSubscription')]
    #[ORM\JoinColumn(nullable: false)]
    private ?Member $member = null;

    public function __construct()
    {
        $this->type = SubscriptionTypeEnum::MEMBER->value;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function toString(): string
    {
        return $this->subscription->getName();
    }

    public function getTypeEnum(): SubscriptionTypeEnum
    {
        return SubscriptionTypeEnum::from($this->type);
    }

    public function getType(): string
    {
        return $this->type;
    }

    public function setTypeEnum(SubscriptionTypeEnum $type): self
    {
        $this->type = $type->value;

        return $this;
    }

    public function getMember(): ?Member
    {
        return $this->member;
    }

    public function getSubscription(): ?Subscription
    {
        return $this->subscription;
    }

    public function setSubscription(?Subscription $subscription): self
    {
        $this->subscription = $subscription;

        return $this;
    }

    public function setMember(?Member $member): self
    {
        $this->member = $member;

        return $this;
    }

    public function __toString()
    {
        return sprintf('%s%s', $this->getSubscription(), substr($this->getTypeEnum()->name, 0, 1));
    }
}
