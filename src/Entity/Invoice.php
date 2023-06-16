<?php

namespace App\Entity;

use App\Repository\InvoiceRepository;
use App\Trait\PriceEntityTrait;
use Doctrine\ORM\Mapping as ORM;
use Gedmo\Timestampable\Traits\TimestampableEntity;

#[ORM\Entity(repositoryClass: InvoiceRepository::class)]
#[ORM\HasLifecycleCallbacks]
class Invoice
{
    use PriceEntityTrait;
    use TimestampableEntity;

    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    protected ?int $id = null;

    #[ORM\Column(nullable: true)]
    protected ?int $reference = null;

    #[ORM\ManyToOne(inversedBy: 'invoices')]
    #[ORM\JoinColumn(nullable: false)]
    protected ?MemberSubscription $memberSubscription = null;

    #[ORM\Column(length: 10, nullable: false, options: ['default' => 'created']) ]
    protected string $status;

    #[ORM\Column(nullable: false, options: ['default' => 0]) ]
    protected int $reminder = 0;

    #[ORM\Column(nullable: true, length: 255)]
    protected ?string $transactionId = null;

    public function __construct()
    {
        $this->status = InvoiceStatusEnum::CREATED->value;
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function setId(?int $id): void
    {
        $this->id = $id;
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

    public function getReminder(): int
    {
        return $this->reminder;
    }

    public function isReminder(): bool
    {
        return $this->reminder > 0;
    }

    public function setReminder(int $reminder): void
    {
        $this->reminder = $reminder;
    }

    public function getTransactionId(): ?string
    {
        return $this->transactionId;
    }

    public function setTransactionId(?string $transactionId): self
    {
        $this->transactionId = $transactionId;

        return $this;
    }
}
