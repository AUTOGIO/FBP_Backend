# The Feynman Summary: How We Taught the Computer to Do Taxes

Imagine you have a very diligent but extremely literal assistant. You tell him, "Go to the tax website, fill out this form, click this button, then that button, and bring me the receipt."

At first, our assistant was getting confused. He'd try to click a button that wasn't there yet, or he'd pick the wrong option because the government website decided "41" actually means "6" (don't ask me why, that's bureaucracy for you!).

## The "Sticky" Problem

We had a problem where the assistant would log in, do one task, log out, and forget everything. We taught him to **stay logged in**. Imagine walking into a room, doing one thing, walking out, closing the door, locking it, then unlocking it again for the next thing. Efficient? No. We fixed that. Now he stays in the room until the job is done.

## The "Invisible" Button

Then there was the "Serviço" and "Imprimir" buttons. Initially, we wanted him to click them. We built a fancy way for him to click gently, and if that didn't work, to poke it harder (JavaScript click).

But then we realized: **we don't actually need to click them right now.** The most important thing is to _submit_ the form. It's like mailing a letter; once it's in the box, the job is done. We don't need to stand there and wait for the postman to wave at us. So, we told the assistant: "Just submit the form. If it says 'Success', believe it and move on. Don't worry about the receipt for now."

## The "Secret Code" (CST 41)

The tax system has a dropdown menu. Humans see "41 - NÃO TRIBUTADA". The computer sees a list of numbers. We found out that under the hood, the computer needs to select number **6** to get option **41**. It's like pressing the 6th floor button in an elevator to get to the 41st floor. We wrote a little note for the assistant: "If you want 41, press 6." And it worked.

## The Result

Now, you can give this assistant a list of 10 people (your batch file). He wakes up, puts on his glasses (activates the environment), goes to the website, and fills out the forms one by one, perfectly, without complaining, and without clicking buttons we don't need. Simple.
