import datetime

import sqlalchemy as sa
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column, Session

DB_FILENAME = 'guild.db'
engine = sa.create_engine(f"sqlite:///{DB_FILENAME}", echo=True, future=True)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    nick: Mapped[str] = mapped_column(unique=True)
    joined_at: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow)
    status: Mapped[str]
    comment: Mapped[str] = mapped_column(default='')

    donations: Mapped[list['Donations']] = relationship('Donations',
                                                        back_populates='user')

    def __repr__(self) -> str:
        return (f"<User: {self.id}> {self.nick} - {self.status}, "
                "{self.joined_at}, {self.comment}")


class Donations(Base):
    __tablename__ = 'donations'

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[int]
    timestamp: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'), nullable=False)

    user: Mapped[User] = relationship('User', back_populates='donations')


Base.metadata.create_all(engine)


def save_donations_to_db(data: dict[str, int]):
    with Session(engine) as session:
        # mark active guild member
        session.query(User).filter(User.nick.in_(data.keys())).update(
            {User.status: 'active'})
        # mark members that left the guild
        session.query(User).filter(User.nick.not_in(data.keys())).update(
            {User.status: 'left'})
        # add new members
        old = set(nick[0] for nick in session.query(User.nick).filter(
            User.nick.in_(data.keys())).all())
        new = set(data.keys())
        session.add_all(User(nick=nick, status='active') for nick in new - old)
        session.commit()

        # add new donation records
        nick_to_id = dict(
            session.query(User.nick,
                          User.id).filter(User.nick.in_(data.keys())))
        session.add_all(
            Donations(
                user_id=nick_to_id[nick],
                amount=amount,
            ) for nick, amount in data.items())
        session.commit()
