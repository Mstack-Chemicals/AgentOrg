# finding-[question-id].md — Schema

## Question
question_id: string
assigned_question: string

## Answer
answer: string
confidence: enum[high, medium, low]

## Sources
sources:
  - title: string
    url: string | null
    type: enum[primary, secondary]
    notes: string | null

## Caveats
caveats: string[]

## Related Risks
related_risks: string[]
