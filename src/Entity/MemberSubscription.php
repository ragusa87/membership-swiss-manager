<?php

namespace App\Entity;

use App\Repository\MemberSubscriptionRepository;
use Doctrine\Common\Collections\ArrayCollection;
use Doctrine\Common\Collections\Collection;
use Doctrine\ORM\Mapping as ORM;
use Gedmo\Timestampable\Traits\TimestampableEntity;
use Symfony\Bridge\Doctrine\Validator\Constraints\UniqueEntity;

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

    #[ORM\Column(length: 255, options: ['default' => 'member'])]
    private string $type;

    #[ORM\ManyToOne(inversedBy: 'subscription')]
    #[ORM\JoinColumn(nullable: false)]
    private ?Subscription $subscription = null;

    #[ORM\ManyToOne(inversedBy: 'memberSubscription')]
    #[ORM\JoinColumn(nullable: false)]
    private ?Member $member = null;

    #[ORM\Column(nullable: true)]
    private ?int $price = 0;

    #[ORM\OneToMany(mappedBy: 'userSubscription', targetEntity: Invoice::class, orphanRemoval: true)]
    private Collection $invoice;

    public function __construct()
    {
        $this->type = SubscriptionTypeEnum::MEMBER->value;
        $this->invoice = new ArrayCollection();
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

    public function getFormattedPrice(): ?string
    {
        $priceInt = $this->getPrice();
        if (null === $priceInt) {
            return null;
        }

        return number_format(float($this->price) / 10.0, 2);
    }

    public function getPrice(): ?int
    {
        return null == $this->price ? $this->getPriceByType() : $this->price;
    }

    private function getPriceByType(): int
    {
        return SubscriptionTypeEnum::MEMBER === $this->getTypeEnum() ? 50 * 100 : 10 * 100;
    }

    public function setPrice(?int $price): self
    {
        $this->price = $price;

        return $this;
    }

    /**
     * @return Collection<int, Invoice>
     */
    public function getInvoice(): Collection
    {
        return $this->invoice;
    }

    public function addInvoice(Invoice $invoice): self
    {
        if (!$this->invoice->contains($invoice)) {
            $this->invoice->add($invoice);
            $invoice->setMemberSubscription($this);
        }

        return $this;
    }

    public function removeInvoice(Invoice $invoice): self
    {
        if ($this->invoice->removeElement($invoice)) {
            // set the owning side to null (unless already changed)
            if ($invoice->getMemberSubscription() === $this) {
                $invoice->setMemberSubscription(null);
            }
        }

        return $this;
    }
}
