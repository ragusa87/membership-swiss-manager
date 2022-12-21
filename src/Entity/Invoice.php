<?php

namespace App\Entity;

use App\Repository\InvoiceRepository;
use App\Trait\PriceEntityTrait;
use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity(repositoryClass: InvoiceRepository::class)]
#[ORM\HasLifecycleCallbacks]
class Invoice
{
    use PriceEntityTrait;

    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    private ?int $id = null;

    #[ORM\Column(nullable: true)]
    private ?int $reference = null;

    #[ORM\ManyToOne(inversedBy: 'invoice')]
    #[ORM\JoinColumn(nullable: false)]
    private ?MemberSubscription $memberSubscription = null;

    #[ORM\Column(length: 10, nullable: false, options: ['default' => 'created']) ]
    private string $status;

    public function __construct()
    {
        $this->status = InvoiceStatusEnum::CREATED->value;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function getReference(): ?int
    {
        return $this->reference ?? $this->id;
    }

    public function setReference(int $number): self
    {
        $this->reference = $number;

        return $this;
    }

    public function getMemberSubscription(): ?MemberSubscription
    {
        return $this->memberSubscription;
    }

    public function setMemberSubscription(?MemberSubscription $memberSubscription): self
    {
        $this->memberSubscription = $memberSubscription;

        return $this;
    }

    public function setStatusFromEnum(InvoiceStatusEnum $enum): static
    {
        $this->status = $enum->value;

        return $this;
    }

    public function getStatusAsEnum(): InvoiceStatusEnum
    {
        return InvoiceStatusEnum::from($this->status);
    }

    public function getStatus(): ?string
    {
        return $this->status;
    }

    public function setStatus(?string $status): static
    {
        $this->status = $status;

        return $this;
    }

    public function setCreatedAtValue()
    {
        $this->createdAt = new \DateTime();
    }
}
