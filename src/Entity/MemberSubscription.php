<?php

namespace App\Entity;

use App\Repository\MemberSubscriptionRepository;
use App\Trait\PriceEntityTrait;
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
    use PriceEntityTrait;

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

    #[ORM\OneToMany(mappedBy: 'memberSubscription', targetEntity: Invoice::class, orphanRemoval: true)]
    private Collection $invoices;

    public function __construct()
    {
        $this->type = SubscriptionTypeEnum::MEMBER->value;
        $this->invoices = new ArrayCollection();
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

    public function setType(string $type): self
    {
        $this->type = $type;

        return $this;
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

    public function toLabel(): string
    {
        return sprintf('%s %s', $this->getMember()->getFullname(), $this->getSubscription()->getName());
    }

    public static function getPriceByType(SubscriptionTypeEnum $enum): int
    {
        return SubscriptionTypeEnum::MEMBER === $enum ? 50 * 100 : 10 * 100;
    }

    /**
     * @return Collection<int, Invoice>
     */
    public function getInvoices(): Collection
    {
        return $this->invoices;
    }

    public function addInvoice(Invoice $invoice): self
    {
        if (!$this->invoices->contains($invoice)) {
            $this->invoices->add($invoice);
            $invoice->setMemberSubscription($this);
        }

        return $this;
    }

    public function removeInvoice(Invoice $invoice): self
    {
        if ($this->invoices->removeElement($invoice)) {
            // set the owning side to null (unless already changed)
            if ($invoice->getMemberSubscription() === $this) {
                $invoice->setMemberSubscription(null);
            }
        }

        return $this;
    }

    public function getPrice(): ?int
    {
        return null == $this->price ? self::getPriceByType($this->getTypeEnum()) : $this->price;
    }

    public function getDueAmount(): int
    {
        $expected = $this->getPrice();
        if (null === $expected) {
            return 0;
        }

        $paid = 0;
        /** @var Invoice $invoice */
        foreach ($this->invoices as $invoice) {
            if (null === $invoice->getPrice()) {
                continue;
            }
            $paid += (InvoiceStatusEnum::PAID === $invoice->getStatusAsEnum() ? 1 : 0) * $invoice->getPrice();
        }

        return $expected - $paid;
    }

    public function generateNewInvoice(): Invoice
    {
        $invoice = new Invoice();
        $invoice->setMemberSubscription($this);
        $invoice->setPrice(self::getPriceByType($this->getTypeEnum()));
        $invoice->setStatusFromEnum(InvoiceStatusEnum::CREATED);
        $this->addInvoice($invoice);

        return $invoice;
    }
}
