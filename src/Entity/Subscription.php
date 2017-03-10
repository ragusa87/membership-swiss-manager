<?php

namespace App\Entity;

use App\Repository\SubscriptionRepository;
use Doctrine\Common\Collections\ArrayCollection;
use Doctrine\Common\Collections\Collection;
use Doctrine\DBAL\Types\Types;
use Doctrine\ORM\Mapping as ORM;
use Gedmo\Timestampable\Traits\TimestampableEntity;

#[ORM\Entity(repositoryClass: SubscriptionRepository::class)]
class Subscription implements \Stringable
{
    use TimestampableEntity;

    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    private ?int $id = null;

    #[ORM\Column(type: Types::STRING, length: 255)]
    private ?string $name = null;

    #[ORM\Column(type: Types::INTEGER, options: ['default' => 6000])]
    private int $priceMember = 6000;

    #[ORM\Column(type: Types::INTEGER, options: ['default' => 1000])]
    private int $priceSupporter = 1000;

    /**
     * @var Collection<int, MemberSubscription>
     */
    #[ORM\OneToMany(mappedBy: 'subscription', targetEntity: MemberSubscription::class, orphanRemoval: true)]
    private Collection $subscription;

    public function __construct()
    {
        $this->subscription = new ArrayCollection();
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function getName(): ?string
    {
        return $this->name;
    }

    public function setName(string $name): self
    {
        $this->name = $name;

        return $this;
    }

    /**
     * @return Collection<int, MemberSubscription>
     */
    public function getSubscription(): Collection
    {
        return $this->subscription;
    }

    public function addSubscription(MemberSubscription $subscription): self
    {
        if (!$this->subscription->contains($subscription)) {
            $this->subscription->add($subscription);
            $subscription->setSubscription($this);
        }

        return $this;
    }

    public function removeSubscription(MemberSubscription $subscription): self
    {
        if ($this->subscription->removeElement($subscription)) {
            // set the owning side to null (unless already changed)
            if ($subscription->getSubscription() === $this) {
                $subscription->setSubscription(null);
            }
        }

        return $this;
    }

    public function setId(?int $id): void
    {
        $this->id = $id;
    }

    public function __toString(): string
    {
        return (string) $this->name;
    }

    public function getPriceMember(): int
    {
        return $this->priceMember;
    }

    public function setPriceMember(int $priceMember): void
    {
        $this->priceMember = $priceMember;
    }

    public function getPriceSupporter(): int
    {
        return $this->priceSupporter;
    }

    public function setPriceSupporter(int $priceSupporter): void
    {
        $this->priceSupporter = $priceSupporter;
    }

    public function getPriceByType(SubscriptionTypeEnum $subscriptionType): ?int
    {
        return match ($subscriptionType) {
            SubscriptionTypeEnum::MEMBER => $this->getPriceMember(),
            SubscriptionTypeEnum::SUPPORTER => $this->getPriceSupporter(),
        };
    }
}
