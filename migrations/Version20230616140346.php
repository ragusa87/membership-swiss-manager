<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

/**
 * Auto-generated Migration: Please modify to your needs!
 */
final class Version20230616140346 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Add comment on membersubscription';
    }

    public function up(Schema $schema): void
    {
        $this->addSql('ALTER TABLE member_subscription ADD COLUMN comment TEXT DEFAULT null NULL');
    }

    public function down(Schema $schema): void
    {
        $this->addSql('ALTER TABLE member_subscription DROP COLUMN comment');
    }
}
